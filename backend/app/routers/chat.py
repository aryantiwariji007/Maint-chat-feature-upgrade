from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Attachment, ChatSession, Message
from app.providers.base import ChatTurn
from app.providers.registry import ProviderNotConfiguredError, get_provider
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _build_history(db: Session, session_id: str) -> list[ChatTurn]:
    messages = db.exec(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    ).all()

    history: list[ChatTurn] = []
    for msg in messages:
        attachments = db.exec(
            select(Attachment).where(Attachment.message_id == msg.id)
        ).all()
        context_blocks = [
            {"filename": a.original_filename, "text": a.extracted_text}
            for a in attachments
            if a.extraction_status == "success" and a.extracted_text
        ]
        history.append(ChatTurn(role=msg.role, text=msg.content, context_blocks=context_blocks))
    return history


@router.post("", response_model=ChatResponse)
def send_chat_message(body: ChatRequest, db: Session = Depends(get_session)):
    chat_session = db.get(ChatSession, body.session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    attachments: list[Attachment] = []
    for attachment_id in body.attachment_ids:
        attachment = db.get(Attachment, attachment_id)
        if attachment is None or attachment.session_id != body.session_id:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")
        if attachment.extraction_status != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Attachment '{attachment.original_filename}' has not been "
                f"successfully extracted (status={attachment.extraction_status}); "
                "cannot use it as context.",
            )
        attachments.append(attachment)

    user_message = Message(session_id=body.session_id, role="user", content=body.content)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    for attachment in attachments:
        attachment.message_id = user_message.id
        db.add(attachment)
    db.commit()

    try:
        provider = get_provider(body.provider)
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    history = _build_history(db, body.session_id)
    result = provider.generate(history)

    assistant_message = Message(
        session_id=body.session_id,
        role="assistant",
        content=result.text,
        provider_used=provider.provider_name,
        model_id_used=result.model_id,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        message_id=assistant_message.id,
        content=assistant_message.content,
        provider_used=provider.provider_name,
        model_id_used=result.model_id,
    )

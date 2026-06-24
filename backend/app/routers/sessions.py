from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import Attachment, ChatSession, Message
from app.schemas import AttachmentOut, MessageOut, SessionCreate, SessionDetail, SessionSummary

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionSummary)
def create_session(body: SessionCreate, db: Session = Depends(get_session)):
    chat_session = ChatSession(default_provider=body.default_provider or settings.default_provider)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


@router.get("", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_session)):
    return db.exec(select(ChatSession).order_by(ChatSession.updated_at.desc())).all()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: str, db: Session = Depends(get_session)):
    chat_session = db.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.exec(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    ).all()

    message_outs = []
    for msg in messages:
        attachments = db.exec(
            select(Attachment).where(Attachment.message_id == msg.id)
        ).all()
        message_outs.append(
            MessageOut(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                provider_used=msg.provider_used,
                model_id_used=msg.model_id_used,
                created_at=msg.created_at,
                attachments=[AttachmentOut(**a.model_dump()) for a in attachments],
            )
        )

    return SessionDetail(
        **chat_session.model_dump(),
        messages=message_outs,
    )

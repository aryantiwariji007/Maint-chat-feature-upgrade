from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.extraction import dispatcher
from app.models import Attachment, ChatSession
from app.schemas import UploadResponse
from app.storage.files import save_upload

router = APIRouter(prefix="/api/upload", tags=["upload"])

IMAGE_KINDS = {"image"}
TABLE_KINDS = {"csv", "xlsx"}


@router.post("", response_model=UploadResponse)
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
):
    chat_session = db.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    kind = dispatcher.classify(file.filename or "", mime_type)
    if kind is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: jpg/png/webp images, csv, xlsx.",
        )

    size_mb = len(content) / (1024 * 1024)
    limit_mb = settings.max_image_upload_mb if kind in IMAGE_KINDS else settings.max_table_upload_mb
    if size_mb > limit_mb:
        raise HTTPException(
            status_code=400, detail=f"File exceeds {limit_mb}MB limit for {kind} uploads."
        )

    path = save_upload(file.filename or "upload", content)

    attachment = Attachment(
        session_id=session_id,
        original_filename=file.filename or path.name,
        mime_type=mime_type,
        kind=kind,
        stored_path=str(path),
        extraction_status="pending",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    result = dispatcher.extract(path, kind, mime_type)

    attachment.extraction_status = result.status
    attachment.extracted_text = result.text
    attachment.extraction_error = result.error
    attachment.extraction_method = result.method
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return UploadResponse(
        attachment_id=attachment.id,
        original_filename=attachment.original_filename,
        kind=attachment.kind,
        extraction_status=attachment.extraction_status,
        extracted_text=attachment.extracted_text,
        extraction_error=attachment.extraction_error,
    )

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    default_provider: str | None = None


class SessionSummary(BaseModel):
    id: str
    title: str
    default_provider: str
    created_at: datetime
    updated_at: datetime


class AttachmentOut(BaseModel):
    id: str
    original_filename: str
    kind: str
    extraction_status: str
    extraction_error: str | None
    extracted_text: str | None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    provider_used: str | None
    model_id_used: str | None
    created_at: datetime
    attachments: list[AttachmentOut] = []


class SessionDetail(SessionSummary):
    messages: list[MessageOut] = []


class UploadResponse(BaseModel):
    attachment_id: str
    original_filename: str
    kind: str
    extraction_status: str
    extracted_text: str | None
    extraction_error: str | None


class ChatRequest(BaseModel):
    session_id: str
    content: str
    provider: str
    attachment_ids: list[str] = []


class ChatResponse(BaseModel):
    message_id: str
    content: str
    provider_used: str
    model_id_used: str

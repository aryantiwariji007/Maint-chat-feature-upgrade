import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class ChatSession(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    title: str = Field(default="New Chat")
    default_provider: str = Field(default="gemini")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Message(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    provider_used: str | None = Field(default=None)
    model_id_used: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now)


class Attachment(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    message_id: str | None = Field(default=None, foreign_key="message.id", index=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    original_filename: str
    mime_type: str
    kind: str  # "image" | "csv" | "xlsx"
    stored_path: str
    extraction_status: str = Field(default="pending")  # pending|success|failed
    extraction_error: str | None = Field(default=None)
    extracted_text: str | None = Field(default=None)
    extraction_method: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now)

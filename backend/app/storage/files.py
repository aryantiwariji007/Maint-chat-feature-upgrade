import uuid
from pathlib import Path

from app.config import UPLOADS_DIR


def save_upload(filename: str, content: bytes) -> Path:
    safe_name = f"{uuid.uuid4()}_{Path(filename).name}"
    dest = UPLOADS_DIR / safe_name
    dest.write_bytes(content)
    return dest

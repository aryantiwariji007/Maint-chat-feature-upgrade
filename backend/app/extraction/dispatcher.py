from pathlib import Path

from app.extraction import vlm_extractor

KIND_BY_EXTENSION = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
}

MIME_BY_KIND_PREFIX = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
}


def classify(filename: str, mime_type: str) -> str | None:
    if mime_type in MIME_BY_KIND_PREFIX:
        return MIME_BY_KIND_PREFIX[mime_type]
    ext = Path(filename).suffix.lower()
    return KIND_BY_EXTENSION.get(ext)


def extract(path: Path, kind: str, mime_type: str):
    if kind == "image":
        return vlm_extractor.extract_image(path, mime_type)
    raise ValueError(f"Unsupported kind: {kind}")

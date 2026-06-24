from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR.parent / ".env"), extra="ignore"
    )

    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    gemini_model: str = "gemini-3.5-flash"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_vlm_model: str = "qwen3-vl:8b-instruct-q4_K_M"

    default_provider: str = "gemini"

    max_image_upload_mb: int = 15
    max_table_upload_mb: int = 5
    max_table_rows: int = 500


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

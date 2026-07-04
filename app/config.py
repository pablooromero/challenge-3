from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sheet_id: str = Field(default="1y6aREOjFrbDd5bKlpt72UBc6svk_pr2wBsAqv_xb_2Y")
    headless: bool = Field(default=False)
    sheets_verify_ssl: bool = Field(default=True)
    playwright_timeout_ms: int = Field(default=15_000)
    evidence_dir: Path = Field(default=ROOT_DIR / "evidence")
    state_file: Path = Field(default=ROOT_DIR / "state" / "submissions.json")
    mapping_file: Path = Field(default=ROOT_DIR / "config" / "mapping.yaml")
    enable_llm: bool = Field(default=False)
    allow_form_post_fallback: bool = Field(default=True)
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-5-mini")


def get_settings() -> Settings:
    settings = Settings()
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    settings.state_file.parent.mkdir(parents=True, exist_ok=True)
    return settings

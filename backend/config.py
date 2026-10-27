"""
MedLens Configuration
=====================
All configuration is loaded from environment variables (or a .env file).
Adjust defaults in .env.example — do not hardcode values here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "ollama", "mock", "groq"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    # ── Embedding ─────────────────────────────────────────────────────────────
    embedding_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size: int = Field(default=400, ge=50, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)

    # ── Retrieval ─────────────────────────────────────────────────────────────
    top_k: int = Field(default=5, ge=1, le=20)
    doc_fallback_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    # ── Storage ───────────────────────────────────────────────────────────────
    upload_dir: Path = Path("data/uploads")
    faiss_index_dir: Path = Path("data/indexes")
    kb_index_path: Path = Path("data/kb_index/medquad.faiss")
    kb_metadata_path: Path = Path("data/kb_index/medquad_meta.pkl")

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "production", "testing"] = "development"
    log_level: str = "INFO"

    @field_validator("chunk_overlap")
    @classmethod
    def overlap_less_than_size(cls, v: int, info) -> int:
        chunk_size = info.data.get("chunk_size", 400)
        if v >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        """Create all required storage directories."""
        for d in (self.upload_dir, self.faiss_index_dir, self.kb_index_path.parent):
            d.mkdir(parents=True, exist_ok=True)


# Single shared instance — import this everywhere
settings = Settings()

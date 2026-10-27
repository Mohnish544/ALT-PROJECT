"""
Settings Route
==============
GET /api/settings  — return current runtime configuration values
PUT /api/settings  — update mutable runtime settings (top_k, fallback threshold)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.api.models import SettingsResponse, UpdateSettingsRequest
from backend.config import settings
from backend.knowledge_base.builder import get_kb_index

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    """Return current system configuration."""
    kb_index = get_kb_index()
    return SettingsResponse(
        embedding_model=settings.embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        doc_fallback_threshold=settings.doc_fallback_threshold,
        llm_provider=settings.llm_provider,
        llm_model=_active_llm_model(),
        kb_available=kb_index is not None and kb_index.total_vectors > 0,
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest) -> SettingsResponse:
    """Update mutable runtime settings."""
    if req.top_k is not None:
        settings.top_k = req.top_k
    if req.doc_fallback_threshold is not None:
        settings.doc_fallback_threshold = req.doc_fallback_threshold
    logger.info("Settings updated: top_k=%s, threshold=%s", settings.top_k, settings.doc_fallback_threshold)
    return get_settings()


def _active_llm_model() -> str:
    try:
        from backend.llm import get_llm_provider
        return get_llm_provider().model
    except Exception:
        return "unknown"

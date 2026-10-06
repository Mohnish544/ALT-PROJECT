"""
Status Route
============
GET /api/status — system health check returning component statuses,
                  document counts, and KB/LLM availability.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.api.models import ComponentStatus, SystemStatusResponse
from backend.config import settings
from backend.knowledge_base.builder import get_kb_index
from backend.llm import get_llm_provider
from backend.retrieval.retriever import list_loaded_doc_ids
from backend.storage.manager import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
def get_status() -> SystemStatusResponse:
    components: list[ComponentStatus] = []
    overall = "healthy"

    # ── Encoder ───────────────────────────────────────────────────────────────
    try:
        from backend.embeddings.encoder import get_encoder
        enc = get_encoder()
        components.append(ComponentStatus(
            name="Embedding Model",
            status="ok",
            detail=f"{enc.model_name} (dim={enc.dim})",
        ))
    except Exception as exc:
        components.append(ComponentStatus(
            name="Embedding Model", status="error", detail=str(exc)
        ))
        overall = "degraded"

    # ── Knowledge Base ────────────────────────────────────────────────────────
    kb_index = get_kb_index()
    if kb_index and kb_index.total_vectors > 0:
        components.append(ComponentStatus(
            name="Medical Knowledge Base",
            status="ok",
            detail=f"{kb_index.total_vectors:,} indexed passages",
        ))
        kb_available = True
        kb_chunk_count = kb_index.total_vectors
    else:
        components.append(ComponentStatus(
            name="Medical Knowledge Base",
            status="warning",
            detail="Not built yet. Run: python scripts/build_kb_index.py",
        ))
        kb_available = False
        kb_chunk_count = 0
        if overall == "healthy":
            overall = "degraded"

    # ── LLM Provider ─────────────────────────────────────────────────────────
    try:
        llm = get_llm_provider()
        if llm.is_available():
            components.append(ComponentStatus(
                name="LLM Provider",
                status="ok",
                detail=f"{llm.name}/{llm.model}",
            ))
        else:
            components.append(ComponentStatus(
                name="LLM Provider",
                status="warning",
                detail=f"{llm.name} unavailable; using mock fallback",
            ))
            if overall == "healthy":
                overall = "degraded"
        llm_provider = llm.name
        llm_model = llm.model
    except Exception as exc:
        components.append(ComponentStatus(
            name="LLM Provider", status="error", detail=str(exc)
        ))
        llm_provider = "error"
        llm_model = "unknown"
        overall = "degraded"

    # ── Document Index ────────────────────────────────────────────────────────
    storage = get_storage()
    all_docs = storage.list_documents()
    ready_docs = [d for d in all_docs if d.status == "ready"]
    loaded_ids = list_loaded_doc_ids()

    components.append(ComponentStatus(
        name="Document Store",
        status="ok",
        detail=f"{len(ready_docs)} document(s) ready, {len(loaded_ids)} index(es) in memory",
    ))

    return SystemStatusResponse(
        status=overall,
        components=components,
        document_count=len(ready_docs),
        kb_available=kb_available,
        kb_chunk_count=kb_chunk_count,
        embedding_model=settings.embedding_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

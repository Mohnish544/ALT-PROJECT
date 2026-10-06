"""
Hybrid Retriever
================
Implements the two-stage retrieval strategy:

Stage 1: Search the user's uploaded document FAISS index.
Stage 2: If max similarity < DOC_FALLBACK_THRESHOLD, fall back to
         the general medical knowledge base index.
Stage 3: Optionally combine results from both when confidence is moderate.

Returns a RetrievalResult with sources clearly tagged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.embeddings.encoder import get_encoder
from backend.embeddings.indexer import FaissIndex, SearchResult
from backend.knowledge_base.builder import get_kb_index

logger = logging.getLogger(__name__)

# Per-session document indexes: {doc_id: FaissIndex}
_doc_indexes: dict[str, FaissIndex] = {}


@dataclass
class RetrievalResult:
    """Full retrieval result returned to the LLM and frontend."""
    query: str
    results: list[SearchResult]                 # Top-k combined results
    source_type: str                            # "document" | "knowledge_base" | "combined" | "none"
    fallback_triggered: bool = False
    doc_max_score: float = 0.0
    kb_max_score: float = 0.0
    strategy: str = "semantic"                  # "semantic" | "baseline_tfidf"
    doc_ids_searched: list[str] = field(default_factory=list)


# ── Index Management (called from API routes) ─────────────────────────────────

def register_doc_index(doc_id: str, index: FaissIndex) -> None:
    """Register a newly built document FAISS index."""
    _doc_indexes[doc_id] = index


def load_doc_index(doc_id: str, index_dir: Path) -> FaissIndex:
    """Load a document index from disk and cache it."""
    if doc_id not in _doc_indexes:
        _doc_indexes[doc_id] = FaissIndex.load(index_dir)
    return _doc_indexes[doc_id]


def unload_doc_index(doc_id: str) -> None:
    """Remove a document index from the cache (on document delete)."""
    _doc_indexes.pop(doc_id, None)


def get_doc_index(doc_id: str) -> Optional[FaissIndex]:
    """Return a cached document index, or None if not loaded."""
    return _doc_indexes.get(doc_id)


def list_loaded_doc_ids() -> list[str]:
    return list(_doc_indexes.keys())


# ── Main Retrieval Entry Point ────────────────────────────────────────────────

def retrieve(
    query: str,
    doc_ids: Optional[list[str]] = None,
    top_k: Optional[int] = None,
    fallback_threshold: Optional[float] = None,
) -> RetrievalResult:
    """
    Retrieve the most relevant chunks for a query.

    Args:
        query:              Natural-language question from the user.
        doc_ids:            Specific document IDs to search (None = all loaded).
        top_k:              Number of results to return.
        fallback_threshold: Override for settings.doc_fallback_threshold.

    Returns:
        RetrievalResult with ranked chunks and provenance metadata.
    """
    k = top_k or settings.top_k
    threshold = fallback_threshold if fallback_threshold is not None \
        else settings.doc_fallback_threshold

    encoder = get_encoder()
    query_vec = encoder.encode_query(query)

    target_doc_ids = doc_ids if doc_ids is not None else list(_doc_indexes.keys())

    # ── Stage 1: Search document index(es) ───────────────────────────────────
    doc_results: list[SearchResult] = []
    doc_max_score = 0.0

    for did in target_doc_ids:
        index = _doc_indexes.get(did)
        if index is None or index.total_vectors == 0:
            continue
        results = index.search(query_vec, top_k=k)
        doc_results.extend(results)

    if doc_results:
        doc_results.sort(key=lambda r: r.score, reverse=True)
        doc_results = doc_results[:k]
        doc_max_score = doc_results[0].score

    # ── Stage 2: Decide on fallback ───────────────────────────────────────────
    fallback_triggered = False
    kb_results: list[SearchResult] = []
    kb_max_score = 0.0

    kb_index = get_kb_index()
    use_kb = False

    if not doc_results:
        # No document loaded at all → use KB directly
        use_kb = True
    elif doc_max_score < threshold:
        # Document match is weak → fall back to KB
        use_kb = True
        fallback_triggered = bool(doc_results)  # True only if we had doc results but they were weak

    if use_kb and kb_index is not None and kb_index.total_vectors > 0:
        kb_results = kb_index.search(query_vec, top_k=k)
        if kb_results:
            kb_max_score = kb_results[0].score

    # ── Stage 3: Compose final result set ────────────────────────────────────
    if doc_results and not use_kb:
        # High-confidence document answer
        final_results = doc_results
        source_type = "document"
    elif doc_results and kb_results and doc_max_score >= threshold * 0.7:
        # Moderate document confidence + KB available → combine
        combined = doc_results + kb_results
        combined.sort(key=lambda r: r.score, reverse=True)
        final_results = combined[:k]
        source_type = "combined"
    elif kb_results:
        # Pure KB fallback
        final_results = kb_results
        source_type = "knowledge_base"
    else:
        # Nothing found
        final_results = []
        source_type = "none"

    logger.info(
        "Retrieval: query=%r source=%s doc_score=%.3f kb_score=%.3f fallback=%s",
        query[:60], source_type, doc_max_score, kb_max_score, fallback_triggered,
    )

    return RetrievalResult(
        query=query,
        results=final_results,
        source_type=source_type,
        fallback_triggered=fallback_triggered,
        doc_max_score=doc_max_score,
        kb_max_score=kb_max_score,
        doc_ids_searched=target_doc_ids,
    )

"""
Chat Route
==========
POST /api/chat     — submit a question, get a grounded answer
GET  /api/chat/history/{session_id}  — retrieve conversation history
DELETE /api/chat/history/{session_id} — clear a session
"""
from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from backend.api.models import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    RetrievalInfo,
    SourceChunk,
)
from backend.llm import get_llm_provider
from backend.retrieval.retriever import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store: {session_id: [{"role": ..., "content": ...}]}
# Production: replace with Redis or a database.
_sessions: dict[str, list[dict]] = defaultdict(list)

MAX_HISTORY_TURNS = 20  # Store at most 20 turns per session


@router.post("/chat", response_model=ChatResponse)
def ask_question(request: ChatRequest) -> ChatResponse:
    """
    Submit a question and receive a grounded, cited answer.

    Flow:
    1. Embed the query.
    2. Retrieve top-k chunks (with KB fallback if needed).
    3. Pass context + history to the LLM provider.
    4. Return answer with source provenance.
    """
    session_id = request.session_id
    history = _sessions[session_id]

    # ── Retrieval ─────────────────────────────────────────────────────────────
    try:
        retrieval = retrieve(
            query=request.question,
            doc_ids=request.doc_ids,
            top_k=request.top_k,
            fallback_threshold=request.fallback_threshold,
        )
    except Exception as exc:
        logger.error("Retrieval error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}")

    # ── LLM Generation ────────────────────────────────────────────────────────
    try:
        provider = get_llm_provider()
        result = provider.generate(
            question=request.question,
            context_chunks=retrieval.results,
            chat_history=history,
            source_type=retrieval.source_type,
        )
    except Exception as exc:
        logger.error("LLM generation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {exc}")

    # ── Update session history ────────────────────────────────────────────────
    history.append({"role": "user", "content": request.question})
    history.append({"role": "assistant", "content": result.answer})
    # Trim to avoid unbounded growth
    _sessions[session_id] = history[-MAX_HISTORY_TURNS * 2:]

    # ── Build response ────────────────────────────────────────────────────────
    source_chunks = [
        SourceChunk(
            chunk_index=r.chunk.chunk_index,
            text=r.chunk.text,
            score=round(r.score, 4),
            doc_id=r.chunk.doc_id,
            source_type=r.chunk.source_type,
            page_hint=r.chunk.page_hint,
            display_source=r.chunk.metadata.get("display_source", r.chunk.doc_id),
        )
        for r in retrieval.results
    ]

    retrieval_info = RetrievalInfo(
        query=request.question,
        source_type=retrieval.source_type,
        fallback_triggered=retrieval.fallback_triggered,
        doc_max_score=round(retrieval.doc_max_score, 4),
        kb_max_score=round(retrieval.kb_max_score, 4),
        num_chunks_retrieved=len(retrieval.results),
        strategy=retrieval.strategy,
    )

    return ChatResponse(
        session_id=session_id,
        question=request.question,
        answer=result.answer or "No answer could be generated.",
        source_type=retrieval.source_type,
        sources=source_chunks,
        retrieval_info=retrieval_info,
        provider=result.provider,
        model=result.model,
        error=result.error,
    )


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
def get_history(session_id: str) -> ChatHistoryResponse:
    history = _sessions.get(session_id, [])
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in history]
    return ChatHistoryResponse(
        session_id=session_id,
        messages=messages,
        turn_count=len(messages) // 2,
    )


@router.delete("/chat/history/{session_id}")
def clear_history(session_id: str) -> dict:
    _sessions.pop(session_id, None)
    return {"session_id": session_id, "message": "Conversation history cleared."}

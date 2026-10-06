"""
FastAPI Pydantic Models
========================
Request/response models for all API endpoints.
Separates API contract from internal domain objects.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Document Models ───────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    file_size: int
    page_count: int
    chunk_count: int
    upload_ts: str
    status: str
    processing_time_s: Optional[float] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DeleteDocumentResponse(BaseModel):
    doc_id: str
    message: str


# ── Processing Job Models ─────────────────────────────────────────────────────

class ProcessingStage(BaseModel):
    stage: str
    status: str          # "pending" | "running" | "done" | "error"
    message: str = ""
    duration_s: Optional[float] = None


class ProcessingJobResponse(BaseModel):
    doc_id: str
    filename: str
    stages: list[ProcessingStage]
    status: str          # "processing" | "ready" | "error"
    page_count: int = 0
    chunk_count: int = 0
    processing_time_s: Optional[float] = None
    error: Optional[str] = None


# ── Chat Models ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str            # "user" | "assistant"
    content: str


class SourceChunk(BaseModel):
    chunk_index: int
    text: str
    score: float
    doc_id: str
    source_type: str     # "document" | "knowledge_base"
    page_hint: Optional[int] = None
    display_source: str = ""


class RetrievalInfo(BaseModel):
    query: str
    source_type: str
    fallback_triggered: bool
    doc_max_score: float
    kb_max_score: float
    num_chunks_retrieved: int
    strategy: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")
    doc_ids: Optional[list[str]] = None   # Which documents to search (None = all)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    fallback_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    source_type: str
    sources: list[SourceChunk]
    retrieval_info: RetrievalInfo
    provider: str
    model: str
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    turn_count: int


# ── Status Models ─────────────────────────────────────────────────────────────

class ComponentStatus(BaseModel):
    name: str
    status: str    # "ok" | "warning" | "error" | "unavailable"
    detail: str = ""


class SystemStatusResponse(BaseModel):
    status: str    # "healthy" | "degraded" | "error"
    components: list[ComponentStatus]
    document_count: int
    kb_available: bool
    kb_chunk_count: int
    embedding_model: str
    llm_provider: str
    llm_model: str


# ── Evaluation Models ─────────────────────────────────────────────────────────

class MetricResult(BaseModel):
    metric: str
    semantic_value: float
    baseline_value: float
    improvement_pct: float


class EvaluationResponse(BaseModel):
    metrics: list[MetricResult]
    total_questions: int
    evaluation_timestamp: str
    notes: str = ""


# ── Settings Models ───────────────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    doc_fallback_threshold: float
    llm_provider: str
    llm_model: str
    kb_available: bool


class UpdateSettingsRequest(BaseModel):
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    doc_fallback_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)

"""
Upload Route
============
POST /api/upload
Accepts a multipart file, runs the full preprocessing + embedding pipeline,
and returns a detailed processing job response with per-stage status.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.api.models import ProcessingJobResponse, ProcessingStage
from backend.config import settings
from backend.embeddings.encoder import get_encoder
from backend.embeddings.indexer import FaissIndex
from backend.preprocessing.cleaner import clean_text
from backend.preprocessing.chunker import chunk_text
from backend.preprocessing.extractor import extract
from backend.retrieval.retriever import register_doc_index
from backend.storage.manager import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE_MB = 50
ALLOWED_TYPES = {"application/pdf", "text/plain",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


@router.post("/upload", response_model=ProcessingJobResponse)
async def upload_document(file: UploadFile = File(...)) -> ProcessingJobResponse:
    """
    Upload and process a healthcare document.

    Stages:
    1. uploading   — save to disk
    2. extracting  — extract text from PDF/DOCX/TXT
    3. cleaning    — normalise and clean text
    4. chunking    — split into overlapping passages
    5. embedding   — generate sentence-transformer vectors
    6. indexing    — build and persist FAISS index
    7. ready       — complete

    Returns a full ProcessingJobResponse with per-stage timing.
    """
    t_total_start = time.perf_counter()

    # ── Validate file ─────────────────────────────────────────────────────────
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Accepted: .pdf, .docx, .txt",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.",
        )

    stages: list[ProcessingStage] = []
    storage = get_storage()

    # ── Stage 1: Save to disk ─────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        record = storage.create_document(
            filename=filename,
            file_bytes=file_bytes,
            file_type=suffix,
        )
        doc_id = record.doc_id
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    stages.append(ProcessingStage(
        stage="uploading", status="done",
        message="File saved securely.",
        duration_s=round(time.perf_counter() - t0, 3),
    ))

    def _error_response(stage_name: str, msg: str, exc: Exception) -> ProcessingJobResponse:
        logger.error("%s failed for %s: %s", stage_name, doc_id, exc)
        storage.update_document(doc_id, status="error")
        stages.append(ProcessingStage(stage=stage_name, status="error", message=str(exc)))
        return ProcessingJobResponse(
            doc_id=doc_id, filename=filename,
            stages=stages, status="error", error=str(exc),
        )

    # ── Stage 2: Extract text ─────────────────────────────────────────────────
    storage.update_document(doc_id, status="extracting")
    t0 = time.perf_counter()
    try:
        extraction = extract(record.file_path)
    except Exception as exc:
        return _error_response("extracting", "Text extraction failed.", exc)

    stages.append(ProcessingStage(
        stage="extracting", status="done",
        message=f"Extracted {extraction.char_count:,} characters from {extraction.page_count} page(s) via {extraction.extraction_method}.",
        duration_s=round(time.perf_counter() - t0, 3),
    ))
    storage.update_document(doc_id, page_count=extraction.page_count)

    # ── Stage 3: Clean text ───────────────────────────────────────────────────
    storage.update_document(doc_id, status="cleaning")
    t0 = time.perf_counter()
    try:
        cleaned = clean_text(extraction.text)
    except Exception as exc:
        return _error_response("cleaning", "Text cleaning failed.", exc)

    stages.append(ProcessingStage(
        stage="cleaning", status="done",
        message=f"Cleaned text: {cleaned.sentence_count} sentences, {len(cleaned.tokens)} tokens.",
        duration_s=round(time.perf_counter() - t0, 3),
    ))

    # ── Stage 4: Chunk ────────────────────────────────────────────────────────
    storage.update_document(doc_id, status="chunking")
    t0 = time.perf_counter()
    try:
        chunks = chunk_text(
            text=cleaned.cleaned_text,
            doc_id=doc_id,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        # Attach display source to each chunk metadata
        for chunk in chunks:
            chunk.metadata["display_source"] = filename
    except Exception as exc:
        return _error_response("chunking", "Document chunking failed.", exc)

    if not chunks:
        return _error_response("chunking", "No text passages could be created.", ValueError("Empty chunks"))

    stages.append(ProcessingStage(
        stage="chunking", status="done",
        message=f"Created {len(chunks)} searchable passages (size={settings.chunk_size}, overlap={settings.chunk_overlap} tokens).",
        duration_s=round(time.perf_counter() - t0, 3),
    ))

    # ── Stage 5: Embed ────────────────────────────────────────────────────────
    storage.update_document(doc_id, status="embedding")
    t0 = time.perf_counter()
    try:
        encoder = get_encoder()
        texts = [c.text for c in chunks]
        vectors = encoder.encode(texts, batch_size=32)
    except Exception as exc:
        return _error_response("embedding", "Embedding generation failed.", exc)

    stages.append(ProcessingStage(
        stage="embedding", status="done",
        message=f"Generated {len(vectors)} embedding vectors (dim={encoder.dim}) using {encoder.model_name}.",
        duration_s=round(time.perf_counter() - t0, 3),
    ))

    # ── Stage 6: FAISS Index ──────────────────────────────────────────────────
    storage.update_document(doc_id, status="indexing")
    t0 = time.perf_counter()
    try:
        index_dir = storage.index_dir_for(doc_id)
        faiss_index = FaissIndex(dim=encoder.dim, index_dir=index_dir)
        faiss_index.add(vectors, chunks)
        faiss_index.save(index_dir)

        # Register in retrieval layer
        register_doc_index(doc_id, faiss_index)
    except Exception as exc:
        return _error_response("indexing", "FAISS indexing failed.", exc)

    stages.append(ProcessingStage(
        stage="indexing", status="done",
        message=f"Index built and persisted ({faiss_index.total_vectors} vectors).",
        duration_s=round(time.perf_counter() - t0, 3),
    ))

    # ── Stage 7: Ready ────────────────────────────────────────────────────────
    total_time = round(time.perf_counter() - t_total_start, 2)
    storage.update_document(
        doc_id, status="ready",
        chunk_count=len(chunks),
        processing_time_s=total_time,
    )

    stages.append(ProcessingStage(
        stage="ready", status="done",
        message=f"Document indexed and ready for queries in {total_time:.1f}s.",
        duration_s=0.0,
    ))

    logger.info(
        "Document %s processed: %d chunks, %.1fs total",
        doc_id, len(chunks), total_time,
    )

    return ProcessingJobResponse(
        doc_id=doc_id,
        filename=filename,
        stages=stages,
        status="ready",
        page_count=extraction.page_count,
        chunk_count=len(chunks),
        processing_time_s=total_time,
    )

"""
Documents Route
===============
GET    /api/documents              — list all documents
GET    /api/documents/{doc_id}     — get one document
DELETE /api/documents/{doc_id}     — delete document + index
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.models import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentResponse,
)
from backend.retrieval.retriever import unload_doc_index
from backend.storage.manager import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(record) -> DocumentResponse:
    return DocumentResponse(
        doc_id=record.doc_id,
        filename=record.filename,
        file_type=record.file_type,
        file_size=record.file_size,
        page_count=record.page_count,
        chunk_count=record.chunk_count,
        upload_ts=record.upload_ts,
        status=record.status,
        processing_time_s=record.processing_time_s,
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    storage = get_storage()
    docs = storage.list_documents()
    return DocumentListResponse(
        documents=[_to_response(d) for d in docs],
        total=len(docs),
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str) -> DocumentResponse:
    storage = get_storage()
    try:
        record = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return _to_response(record)


@router.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse)
def delete_document(doc_id: str) -> DeleteDocumentResponse:
    storage = get_storage()
    try:
        record = storage.get_document(doc_id)
        filename = record.filename
        storage.delete_document(doc_id)
        unload_doc_index(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    except Exception as exc:
        logger.error("Failed to delete document %s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {exc}")

    return DeleteDocumentResponse(
        doc_id=doc_id,
        message=f"'{filename}' has been removed from the system.",
    )

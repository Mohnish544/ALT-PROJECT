"""
Document Storage Manager
========================
Manages the lifecycle of uploaded documents and their per-document
FAISS indexes.

Registry: JSON file at data/indexes/registry.json
  {
    "<doc_id>": {
      "doc_id": "...",
      "filename": "...",
      "file_type": "pdf",
      "file_size": 123456,
      "page_count": 12,
      "chunk_count": 45,
      "upload_ts": "2024-01-01T00:00:00Z",
      "status": "ready",
      "index_dir": "data/indexes/<doc_id>"
    }
  }
"""
from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

REGISTRY_FILE = settings.faiss_index_dir / "registry.json"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class DocumentRecord:
    """Mutable document record stored in the registry."""

    def __init__(self, data: dict) -> None:
        self._d = data

    # ── Accessors ─────────────────────────────────────────────────────────────
    @property
    def doc_id(self) -> str: return self._d["doc_id"]
    @property
    def filename(self) -> str: return self._d["filename"]
    @property
    def file_type(self) -> str: return self._d["file_type"]
    @property
    def file_size(self) -> int: return self._d["file_size"]
    @property
    def page_count(self) -> int: return self._d.get("page_count", 0)
    @property
    def chunk_count(self) -> int: return self._d.get("chunk_count", 0)
    @property
    def upload_ts(self) -> str: return self._d["upload_ts"]
    @property
    def status(self) -> str: return self._d["status"]
    @property
    def index_dir(self) -> Path: return Path(self._d["index_dir"])
    @property
    def file_path(self) -> Path: return Path(self._d["file_path"])
    @property
    def processing_time_s(self) -> Optional[float]: return self._d.get("processing_time_s")

    def update(self, **kwargs) -> None:
        self._d.update(kwargs)

    def to_dict(self) -> dict:
        return dict(self._d)


class StorageManager:
    """
    Handles:
    - Saving uploaded files to disk.
    - Creating/loading the document registry.
    - Providing index paths for the embedding layer.
    - Deleting documents + indexes.
    """

    def __init__(self) -> None:
        settings.ensure_dirs()
        self._registry: dict[str, dict] = self._load_registry()

    # ── Registry I/O ─────────────────────────────────────────────────────────

    def _load_registry(self) -> dict[str, dict]:
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Registry corrupted, starting fresh: %s", exc)
        return {}

    def _save_registry(self) -> None:
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, indent=2)

    # ── Document CRUD ─────────────────────────────────────────────────────────

    def create_document(
        self,
        filename: str,
        file_bytes: bytes,
        file_type: str,
    ) -> DocumentRecord:
        """Save the uploaded file and create a registry entry with status='uploading'."""
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        doc_id = uuid.uuid4().hex
        safe_filename = f"{doc_id}{suffix}"
        file_path = settings.upload_dir / safe_filename

        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_bytes)

        index_dir = settings.faiss_index_dir / doc_id

        record_data = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_type.lstrip("."),
            "file_size": len(file_bytes),
            "file_path": str(file_path),
            "index_dir": str(index_dir),
            "page_count": 0,
            "chunk_count": 0,
            "upload_ts": datetime.now(timezone.utc).isoformat(),
            "status": "uploading",
            "processing_time_s": None,
        }
        self._registry[doc_id] = record_data
        self._save_registry()
        return DocumentRecord(record_data)

    def update_document(self, doc_id: str, **kwargs) -> DocumentRecord:
        """Update fields on an existing registry entry."""
        if doc_id not in self._registry:
            raise KeyError(f"Document {doc_id!r} not found in registry.")
        self._registry[doc_id].update(kwargs)
        self._save_registry()
        return DocumentRecord(self._registry[doc_id])

    def get_document(self, doc_id: str) -> DocumentRecord:
        if doc_id not in self._registry:
            raise KeyError(f"Document {doc_id!r} not found.")
        return DocumentRecord(self._registry[doc_id])

    def list_documents(self) -> list[DocumentRecord]:
        """Return all documents sorted by upload time (newest first)."""
        docs = [DocumentRecord(d) for d in self._registry.values()]
        docs.sort(key=lambda d: d.upload_ts, reverse=True)
        return docs

    def delete_document(self, doc_id: str) -> None:
        """Remove file, FAISS index directory, and registry entry."""
        if doc_id not in self._registry:
            raise KeyError(f"Document {doc_id!r} not found.")

        record = DocumentRecord(self._registry[doc_id])

        # Delete uploaded file
        try:
            record.file_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", record.file_path, exc)

        # Delete FAISS index directory
        try:
            if record.index_dir.exists():
                shutil.rmtree(record.index_dir)
        except OSError as exc:
            logger.warning("Could not delete index dir %s: %s", record.index_dir, exc)

        del self._registry[doc_id]
        self._save_registry()
        logger.info("Deleted document %s (%s)", doc_id, record.filename)

    def index_dir_for(self, doc_id: str) -> Path:
        """Return the FAISS index directory for a document."""
        return settings.faiss_index_dir / doc_id


# Module-level singleton
_storage_manager: Optional[StorageManager] = None


def get_storage() -> StorageManager:
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager

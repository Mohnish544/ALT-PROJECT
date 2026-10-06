"""
MedQuAD Knowledge Base Loader
==============================
Loads the MedQuAD dataset (pre-downloaded JSONL file) into Chunk objects
ready for embedding and FAISS indexing.

MedQuAD source: https://github.com/abachaa/MedQuAD
License: Apache 2.0

Each entry in medquad.jsonl has the structure:
  {
    "question": "...",
    "answer": "...",
    "source": "NIH/...",
    "focus": "Disease or condition name",
    "qtype": "symptoms | treatment | causes | ..."
  }
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Generator

from backend.preprocessing.chunker import Chunk, chunk_text
from backend.config import settings

logger = logging.getLogger(__name__)

MEDQUAD_JSONL = Path("data/medquad/medquad.jsonl")
KB_SOURCE_TAG = "knowledge_base"


def _iter_entries(path: Path) -> Generator[dict, None, None]:
    """Stream entries from the JSONL file line by line."""
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping line %d (JSON error): %s", lineno, exc)


def load_kb_chunks(
    max_entries: int | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """
    Load MedQuAD and convert to chunks suitable for embedding.

    Strategy:
    - Use the question as a "prefix" for context-aware embedding.
    - Chunk the answer text (answers can be very long).
    - Attach source metadata to each chunk.

    Args:
        max_entries:   Limit entries for testing/demo (None = all ~47k).
        chunk_size:    Token budget per chunk (defaults to settings.chunk_size).
        chunk_overlap: Overlap tokens (defaults to settings.chunk_overlap).

    Returns:
        List of Chunk objects tagged source_type="knowledge_base".
    """
    c_size = chunk_size or settings.chunk_size
    c_overlap = chunk_overlap or settings.chunk_overlap

    if not MEDQUAD_JSONL.exists():
        logger.warning(
            "MedQuAD JSONL not found at %s. "
            "Run `python scripts/download_medquad.py` to fetch it.",
            MEDQUAD_JSONL,
        )
        return []

    all_chunks: list[Chunk] = []
    entry_count = 0

    for entry in _iter_entries(MEDQUAD_JSONL):
        if max_entries is not None and entry_count >= max_entries:
            break

        question = entry.get("question", "").strip()
        answer = entry.get("answer", "").strip()
        source = entry.get("source", "MedQuAD")
        focus = entry.get("focus", "")
        qtype = entry.get("qtype", "")

        if not answer:
            continue

        # Prepend question for richer context during embedding
        full_text = f"Q: {question}\nA: {answer}" if question else answer

        entry_id = f"kb_{entry_count:06d}"
        chunks = chunk_text(
            text=full_text,
            doc_id=entry_id,
            chunk_size=c_size,
            chunk_overlap=c_overlap,
            source_type=KB_SOURCE_TAG,
        )

        # Attach KB-specific metadata
        for chunk in chunks:
            chunk.metadata.update({
                "kb_source": source,
                "kb_focus": focus,
                "kb_qtype": qtype,
                "kb_question": question,
                "display_source": f"Medical Knowledge Base — {focus}" if focus else "Medical Knowledge Base",
            })

        all_chunks.extend(chunks)
        entry_count += 1

    logger.info("Loaded %d MedQuAD entries → %d chunks", entry_count, len(all_chunks))
    return all_chunks

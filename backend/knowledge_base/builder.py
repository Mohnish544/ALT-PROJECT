"""
Knowledge Base Builder
=======================
Builds and saves the general medical knowledge FAISS index from MedQuAD chunks.
Called once at setup time (or via ``scripts/build_kb_index.py``).
Loaded at app startup from the pre-built index files.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.embeddings.encoder import get_encoder
from backend.embeddings.indexer import FaissIndex
from backend.knowledge_base.loader import load_kb_chunks

logger = logging.getLogger(__name__)

# Cached global KB index (loaded once at startup)
_kb_index: Optional[FaissIndex] = None


def build_kb_index(
    save_path: Optional[Path] = None,
    max_entries: Optional[int] = None,
) -> FaissIndex:
    """
    Build the KB FAISS index from MedQuAD.

    Args:
        save_path:   Directory to save index files (default: settings.kb_index_path.parent).
        max_entries: Limit entries for fast demo build.

    Returns:
        Populated FaissIndex.
    """
    save_dir = save_path or settings.kb_index_path.parent
    encoder = get_encoder()

    logger.info("Loading MedQuAD chunks...")
    chunks = load_kb_chunks(max_entries=max_entries)

    if not chunks:
        logger.error("No KB chunks found. KB index will be empty.")
        return FaissIndex(dim=encoder.dim, index_dir=save_dir)

    logger.info("Encoding %d KB chunks (this may take several minutes)...", len(chunks))
    t0 = time.time()
    texts = [c.text for c in chunks]
    vectors = encoder.encode(texts, batch_size=64, show_progress=True)
    elapsed = time.time() - t0
    logger.info("Encoded %d chunks in %.1fs", len(chunks), elapsed)

    index = FaissIndex(dim=encoder.dim, index_dir=save_dir)
    index.add(vectors, chunks)
    index.save(save_dir)

    logger.info("KB index built: %d vectors saved to %s", index.total_vectors, save_dir)
    return index


def load_kb_index() -> Optional[FaissIndex]:
    """
    Load the pre-built KB FAISS index from disk.
    Returns None if not yet built (caller should handle gracefully).
    """
    global _kb_index
    if _kb_index is not None:
        return _kb_index

    index_dir = settings.kb_index_path.parent
    encoder = get_encoder()

    try:
        _kb_index = FaissIndex.load(index_dir)
        logger.info("KB index loaded: %d vectors", _kb_index.total_vectors)
        return _kb_index
    except FileNotFoundError:
        logger.warning(
            "KB index not found at %s. Run `python scripts/build_kb_index.py`.",
            index_dir,
        )
        return None


def get_kb_index() -> Optional[FaissIndex]:
    """Return the cached KB index (call load_kb_index() at startup first)."""
    return _kb_index

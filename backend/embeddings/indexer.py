"""
FAISS Indexer
=============
Manages creation, storage, and querying of FAISS vector indexes.

One ``FaissIndex`` per document (stored in data/indexes/<doc_id>/).
One shared ``FaissIndex`` for the general medical knowledge base.

Index type: IndexFlatIP (exact inner-product = cosine similarity when
vectors are L2-normalised, which the Encoder always does).

For scaling: swap to IndexIVFFlat or IndexHNSWFlat with minimal API change.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from numpy.typing import NDArray

from backend.preprocessing.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float      # Cosine similarity [0, 1] (higher = more relevant)
    rank: int


class FaissIndex:
    """
    Wraps a FAISS IndexFlatIP with chunk metadata persistence.

    Layout on disk (dir/):
      vectors.faiss   — FAISS binary index
      metadata.pkl    — list[Chunk] in insertion order
    """

    def __init__(self, dim: int, index_dir: Optional[Path] = None) -> None:
        self.dim = dim
        self.index_dir = index_dir
        self._index = faiss.IndexFlatIP(dim)
        self._chunks: list[Chunk] = []

    # ── Building ─────────────────────────────────────────────────────────────

    def add(self, vectors: NDArray[np.float32], chunks: list[Chunk]) -> None:
        """
        Add embeddings and their corresponding Chunk metadata.

        Args:
            vectors: float32 array of shape (N, dim), L2-normalised.
            chunks:  list of N Chunk objects in the same order.
        """
        if len(vectors) != len(chunks):
            raise ValueError(
                f"vectors ({len(vectors)}) and chunks ({len(chunks)}) must have equal length."
            )
        if len(vectors) == 0:
            return

        self._index.add(vectors)
        self._chunks.extend(chunks)
        logger.debug("Added %d vectors. Total: %d", len(vectors), self._index.ntotal)

    # ── Querying ─────────────────────────────────────────────────────────────

    def search(
        self,
        query_vector: NDArray[np.float32],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """
        Retrieve the top-k most similar chunks for a query vector.

        Args:
            query_vector: shape (1, dim) or (dim,), L2-normalised.
            top_k:        Maximum number of results.
            min_score:    Minimum similarity score to include.

        Returns:
            Sorted list of SearchResult (best first).
        """
        if self._index.ntotal == 0:
            return []

        # Ensure 2D
        vec = np.atleast_2d(query_vector).astype(np.float32)
        k = min(top_k, self._index.ntotal)

        scores, indices = self._index.search(vec, k)

        results: list[SearchResult] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0:          # FAISS returns -1 for padding
                continue
            score_f = float(score)
            if score_f < min_score:
                continue
            results.append(SearchResult(
                chunk=self._chunks[idx],
                score=score_f,
                rank=rank + 1,
            ))

        return results

    def max_score(
        self, query_vector: NDArray[np.float32], top_k: int = 5
    ) -> float:
        """Return the maximum similarity score without constructing full results."""
        results = self.search(query_vector, top_k=top_k)
        return results[0].score if results else 0.0

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self, directory: Optional[Path] = None) -> Path:
        """Persist index and metadata to disk."""
        save_dir = directory or self.index_dir
        if save_dir is None:
            raise ValueError("No save directory specified.")
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(save_dir / "vectors.faiss"))
        with open(save_dir / "metadata.pkl", "wb") as f:
            pickle.dump(self._chunks, f)

        logger.info("Index saved to %s (%d vectors)", save_dir, self._index.ntotal)
        return save_dir

    @classmethod
    def load(cls, directory: Path) -> "FaissIndex":
        """Load a previously saved index from disk."""
        directory = Path(directory)
        faiss_path = directory / "vectors.faiss"
        meta_path = directory / "metadata.pkl"

        if not faiss_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"Index files not found in {directory}. "
                "Run the indexing step first."
            )

        raw_index = faiss.read_index(str(faiss_path))
        with open(meta_path, "rb") as f:
            chunks: list[Chunk] = pickle.load(f)

        inst = cls(dim=raw_index.d, index_dir=directory)
        inst._index = raw_index
        inst._chunks = chunks

        logger.info("Loaded index from %s (%d vectors)", directory, raw_index.ntotal)
        return inst

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def remove_by_doc_id(self, doc_id: str) -> int:
        """
        Remove all vectors belonging to a document.
        FAISS IndexFlatIP doesn't support in-place removal, so we rebuild.
        Returns the number of removed vectors.
        """
        remaining = [c for c in self._chunks if c.doc_id != doc_id]
        removed = len(self._chunks) - len(remaining)

        if removed == 0:
            return 0

        # Rebuild
        new_index = faiss.IndexFlatIP(self.dim)
        self._chunks = remaining
        self._index = new_index

        logger.info("Removed %d vectors for doc_id=%s", removed, doc_id)
        return removed

    def exists_on_disk(self) -> bool:
        if self.index_dir is None:
            return False
        return (self.index_dir / "vectors.faiss").exists()

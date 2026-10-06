"""
TF-IDF Baseline Retriever
==========================
Implements a BM25 / TF-IDF bag-of-words retriever for comparison
against the semantic embedding approach in evaluation.

Used in:
- backend/evaluation/evaluator.py (baseline vs. semantic comparison)
- API status endpoint to show both retrieval methods are available.

Not used as the primary retrieval path in production.
"""
from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Optional

from backend.preprocessing.cleaner import clean_text
from backend.preprocessing.chunker import Chunk

logger = logging.getLogger(__name__)


class TFIDFRetriever:
    """
    Lightweight BM25-inspired TF-IDF retriever.

    Uses scikit-learn's TfidfVectorizer for reproducibility
    and compatibility with the course's NLP/ML stack.
    """

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=50_000,
            sublinear_tf=True,      # log(1+tf) — better for long docs
            min_df=1,
        )
        self._matrix = None
        self._chunks: list[Chunk] = []
        self._fitted = False
        self._np = np

    def fit(self, chunks: list[Chunk]) -> None:
        """Build TF-IDF matrix from chunk texts."""
        if not chunks:
            logger.warning("TFIDFRetriever.fit() called with empty chunk list.")
            return

        # Use lemmatised tokens for better recall
        corpus = []
        for chunk in chunks:
            cleaned = clean_text(chunk.text, remove_stopwords=True)
            corpus.append(" ".join(cleaned.tokens) if cleaned.tokens else chunk.text)

        self._matrix = self._vectorizer.fit_transform(corpus)
        self._chunks = list(chunks)
        self._fitted = True
        logger.info("TF-IDF matrix built: %d chunks × %d features",
                    self._matrix.shape[0], self._matrix.shape[1])

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Retrieve top-k chunks by TF-IDF cosine similarity.

        Returns:
            List of (Chunk, score) tuples sorted by score descending.
        """
        if not self._fitted or self._matrix is None:
            return []

        cleaned = clean_text(query, remove_stopwords=True)
        query_str = " ".join(cleaned.tokens) if cleaned.tokens else query
        query_vec = self._vectorizer.transform([query_str])

        # Cosine similarity via dot product (vectors are L2-normalised by TF-IDF)
        scores = (self._matrix @ query_vec.T).toarray().flatten()
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self._chunks[idx], float(scores[idx])))

        return results


# Module-level instance reused across evaluations
_baseline: Optional[TFIDFRetriever] = None


def get_baseline() -> TFIDFRetriever:
    global _baseline
    if _baseline is None:
        _baseline = TFIDFRetriever()
    return _baseline

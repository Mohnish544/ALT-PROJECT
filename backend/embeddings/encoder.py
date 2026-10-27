"""
Sentence-Transformer Encoder
=============================
Singleton wrapper around a HuggingFace sentence-transformers model.
Encodes text passages (chunks) and queries into fixed-size dense vectors.

Default model: pritamdeka/S-PubMedBert-MS-MARCO
  - Fine-tuned on biomedical/PubMed data with MS-MARCO retrieval objective.
  - Produces 768-dim embeddings suitable for cosine similarity search.
  - Downloads ~400 MB from HuggingFace Hub on first run.

Fallback: all-MiniLM-L6-v2 (384-dim, 80 MB, general-purpose).
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from backend.config import settings

logger = logging.getLogger(__name__)

# Dimensionality per model (used for index initialisation before model loads)
KNOWN_DIMS: dict[str, int] = {
    "pritamdeka/S-PubMedBert-MS-MARCO": 768,
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
}


class Encoder:
    """
    Thread-safe sentence-transformer encoder.
    Call ``get_encoder()`` to get the module-level singleton.
    """

    def __init__(self, model_name: str) -> None:
        logger.info("Loading embedding model: %s", model_name)
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:
            fallback = "all-MiniLM-L6-v2"
            logger.warning(
                "Failed to load %s (%s). Falling back to %s.",
                model_name, exc, fallback,
            )
            self._model = SentenceTransformer(fallback)
            model_name = fallback

        self.model_name = model_name
        dim_fn = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        self.dim: int = dim_fn()
        logger.info("Encoder ready. Dimension: %d", self.dim)

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> NDArray[np.float32]:
        """
        Encode a list of strings into an (N, dim) float32 array.

        Args:
            texts:         Input strings.
            batch_size:    Batch size for encoding.
            show_progress: Show tqdm progress bar.
            normalize:     L2-normalise outputs (required for cosine sim via inner product).

        Returns:
            numpy array of shape (N, dim), dtype float32.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )
        return vectors.astype(np.float32)

    def encode_query(self, query: str) -> NDArray[np.float32]:
        """Encode a single query string. Returns shape (1, dim)."""
        return self.encode([query])


# ── Module-level singleton ────────────────────────────────────────────────────

_encoder_instance: Optional[Encoder] = None


def get_encoder() -> Encoder:
    """Return (or lazily initialise) the global encoder singleton."""
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = Encoder(settings.embedding_model)
    return _encoder_instance

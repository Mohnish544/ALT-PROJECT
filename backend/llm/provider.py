"""
LLM Provider Abstract Base
===========================
Defines the interface that all LLM providers must implement.
Swap providers by changing LLM_PROVIDER in .env — no code changes needed.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from backend.embeddings.indexer import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    answer: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'openai', 'anthropic', 'ollama')."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier."""

    @abstractmethod
    def generate(
        self,
        question: str,
        context_chunks: list[SearchResult],
        chat_history: Optional[list[dict]] = None,
        source_type: str = "document",
    ) -> GenerationResult:
        """
        Generate a grounded answer.

        Args:
            question:      User's question.
            context_chunks: Retrieved passages with scores.
            chat_history:  Previous turns as [{"role": "user"|"assistant", "content": "..."}].
            source_type:   "document" | "knowledge_base" | "combined" | "none".

        Returns:
            GenerationResult with answer text and token counts.
        """

    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""
        return True

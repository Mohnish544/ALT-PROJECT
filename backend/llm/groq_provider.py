"""Groq LLM Provider."""
from __future__ import annotations

import logging
from typing import Optional

from backend.config import settings
from backend.embeddings.indexer import SearchResult
from backend.llm.provider import LLMProvider, GenerationResult
from backend.llm.prompts import build_messages

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """
    LLM provider using Groq's high-speed, free cloud inference API.
    Model: llama-3.3-70b-versatile or llama-3.1-8b-instant (configurable via GROQ_MODEL in .env).
    Requires a free API key from https://console.groq.com/keys
    """

    def __init__(self) -> None:
        try:
            import openai
            self._client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key or "no-key",
            )
            self._available = True
        except Exception as exc:
            logger.warning("Groq client init failed: %s", exc)
            self._client = None
            self._available = False

    @property
    def name(self) -> str:
        return "groq"

    @property
    def model(self) -> str:
        return settings.groq_model

    def is_available(self) -> bool:
        return self._available and bool(settings.groq_api_key)

    def generate(
        self,
        question: str,
        context_chunks: list[SearchResult],
        chat_history: Optional[list[dict]] = None,
        source_type: str = "document",
    ) -> GenerationResult:
        messages = build_messages(question, context_chunks, source_type, chat_history)

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            answer = response.choices[0].message.content or ""
            usage = response.usage
            return GenerationResult(
                answer=answer,
                model=self.model,
                provider=self.name,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )
        except Exception as exc:
            logger.error("Groq generation error: %s", exc)
            return GenerationResult(
                answer="",
                model=self.model,
                provider=self.name,
                error=str(exc),
            )

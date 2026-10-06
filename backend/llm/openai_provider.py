"""OpenAI LLM Provider."""
from __future__ import annotations

import logging
from typing import Optional

from backend.config import settings
from backend.embeddings.indexer import SearchResult
from backend.llm.provider import LLMProvider, GenerationResult
from backend.llm.prompts import build_messages, build_no_context_answer

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    LLM provider using the OpenAI Chat Completions API.
    Model: gpt-4o-mini (configurable via OPENAI_MODEL in .env).
    """

    def __init__(self) -> None:
        try:
            import openai
            self._client = openai.OpenAI(api_key=settings.openai_api_key)
            self._available = True
        except Exception as exc:
            logger.warning("OpenAI client init failed: %s", exc)
            self._client = None
            self._available = False

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return settings.openai_model

    def is_available(self) -> bool:
        return self._available and bool(settings.openai_api_key)

    def generate(
        self,
        question: str,
        context_chunks: list[SearchResult],
        chat_history: Optional[list[dict]] = None,
        source_type: str = "document",
    ) -> GenerationResult:
        if not context_chunks:
            return GenerationResult(
                answer=build_no_context_answer(source_type),
                model=self.model, provider=self.name,
            )

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
            logger.error("OpenAI generation error: %s", exc)
            return GenerationResult(
                answer="",
                model=self.model,
                provider=self.name,
                error=str(exc),
            )

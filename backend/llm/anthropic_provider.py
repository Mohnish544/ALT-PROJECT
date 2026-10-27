"""Anthropic Claude LLM Provider."""
from __future__ import annotations

import logging
from typing import Optional

from backend.config import settings
from backend.embeddings.indexer import SearchResult
from backend.llm.provider import LLMProvider, GenerationResult
from backend.llm.prompts import build_messages, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    LLM provider using Anthropic's Messages API.
    Model: claude-3-haiku-20240307 (fast, cost-effective, good for RAG).
    """

    def __init__(self) -> None:
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self._available = True
        except Exception as exc:
            logger.warning("Anthropic client init failed: %s", exc)
            self._client = None
            self._available = False

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return settings.anthropic_model

    def is_available(self) -> bool:
        return self._available and bool(settings.anthropic_api_key)

    def generate(
        self,
        question: str,
        context_chunks: list[SearchResult],
        chat_history: Optional[list[dict]] = None,
        source_type: str = "document",
    ) -> GenerationResult:


        # Anthropic uses system separately from messages
        messages = build_messages(question, context_chunks, source_type, chat_history)
        # Remove system message — pass separately to Anthropic API
        system = SYSTEM_PROMPT
        user_messages = [m for m in messages if m["role"] != "system"]

        try:
            response = self._client.messages.create(
                model=self.model,
                system=system,
                messages=user_messages,
                temperature=0.2,
                max_tokens=1024,
            )
            answer = response.content[0].text if response.content else ""
            return GenerationResult(
                answer=answer,
                model=self.model,
                provider=self.name,
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
            )
        except Exception as exc:
            logger.error("Anthropic generation error: %s", exc)
            return GenerationResult(
                answer="", model=self.model, provider=self.name, error=str(exc),
            )

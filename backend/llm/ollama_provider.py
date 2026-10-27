"""Ollama Local LLM Provider."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from backend.config import settings
from backend.embeddings.indexer import SearchResult
from backend.llm.provider import LLMProvider, GenerationResult
from backend.llm.prompts import build_messages

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    LLM provider using a locally running Ollama instance.
    No API key required. Requires `ollama serve` running on the host.
    Default model: mistral (configurable via OLLAMA_MODEL in .env).
    """

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return settings.ollama_model

    def is_available(self) -> bool:
        try:
            response = httpx.get(
                f"{settings.ollama_base_url}/api/tags", timeout=3.0
            )
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        question: str,
        context_chunks: list[SearchResult],
        chat_history: Optional[list[dict]] = None,
        source_type: str = "document",
    ) -> GenerationResult:
        messages = build_messages(question, context_chunks, source_type, chat_history)

        try:
            response = httpx.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 1024},
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "")
            return GenerationResult(
                answer=answer, model=self.model, provider=self.name,
            )
        except Exception as exc:
            logger.error("Ollama generation error: %s", exc)
            return GenerationResult(
                answer="", model=self.model, provider=self.name, error=str(exc),
            )


class MockProvider(LLMProvider):
    """
    Mock provider for testing and demo — returns a template answer
    referencing the retrieved passages without calling any API.
    """

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-v1"

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

        source_label = {
            "document": "the uploaded document",
            "knowledge_base": "the medical knowledge base",
            "combined": "both the document and medical knowledge base",
        }.get(source_type, "retrieved sources")

        top_chunk = context_chunks[0].chunk.text[:300]
        answer = (
            f"Based on {source_label}, here is the most relevant information "
            f"for your question about **\"{question}\"**:\n\n"
            f"> {top_chunk}{'...' if len(context_chunks[0].chunk.text) > 300 else ''}\n\n"
            f"{len(context_chunks)} passage(s) were retrieved with a top relevance "
            f"score of {context_chunks[0].score:.0%}.\n\n"
            f"⚕ This information is for educational reference only and does not "
            f"replace professional medical advice."
        )
        return GenerationResult(
            answer=answer, model=self.model, provider=self.name,
        )

"""
LLM Package
============
Exports the provider factory function ``get_llm_provider()`` which
returns the appropriate provider based on settings.LLM_PROVIDER.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.config import settings
from backend.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_provider_instance: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """
    Return (or lazily initialise) the configured LLM provider.
    Falls back to MockProvider if the configured provider is unavailable.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    from backend.llm.ollama_provider import MockProvider

    provider_map = {
        "openai": _load_openai,
        "anthropic": _load_anthropic,
        "ollama": _load_ollama,
        "groq": _load_groq,
        "mock": lambda: MockProvider(),
    }

    loader = provider_map.get(settings.llm_provider, lambda: MockProvider())
    provider = loader()

    if not provider.is_available():
        logger.warning(
            "LLM provider '%s' is not available. Falling back to MockProvider.",
            settings.llm_provider,
        )
        provider = MockProvider()

    _provider_instance = provider
    logger.info("LLM provider: %s / model: %s", provider.name, provider.model)
    return _provider_instance


def _load_openai() -> LLMProvider:
    from backend.llm.openai_provider import OpenAIProvider
    return OpenAIProvider()


def _load_anthropic() -> LLMProvider:
    from backend.llm.anthropic_provider import AnthropicProvider
    return AnthropicProvider()


def _load_ollama() -> LLMProvider:
    from backend.llm.ollama_provider import OllamaProvider
    return OllamaProvider()


def _load_groq() -> LLMProvider:
    from backend.llm.groq_provider import GroqProvider
    return GroqProvider()


__all__ = ["get_llm_provider", "LLMProvider"]

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.services.llm.mock_provider import MockLLMProvider


def build_llm(kind: str | None = None) -> LLMProvider:
    s = get_settings()
    kind = kind or s.llm_provider
    if kind == "openai":
        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(s.openai_api_key, s.openai_chat_model, s.openai_base_url)
    if kind == "anthropic":
        from app.services.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    return MockLLMProvider()


@lru_cache
def get_llm() -> LLMProvider:
    return build_llm()


__all__ = ["LLMMessage", "LLMProvider", "LLMResponse", "MockLLMProvider", "build_llm", "get_llm"]

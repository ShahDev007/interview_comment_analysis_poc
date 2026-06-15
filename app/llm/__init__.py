"""LLM seam package. ``get_llm_client()`` is the single switch between mock and real Claude."""
from __future__ import annotations

from app.config import settings
from app.llm.base import LLMClient


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Return the configured LLMClient. Default 'mock' runs fully offline."""
    provider = (provider or settings.llm_provider).lower()
    if provider == "mock":
        from app.llm.mock_client import MockLLMClient

        return MockLLMClient()
    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient()
    raise ValueError(f"Unknown LLM_PROVIDER={provider!r}. Use 'mock' or 'anthropic'.")

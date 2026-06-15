"""The LLM seam.

``LLMClient`` is the single swap point between the offline mock and a real Claude model. It is
deliberately *generic* -- it knows nothing about moderation. It takes a system prompt, a user
message, and the Pydantic schema the caller wants back, and returns a validated instance plus
metadata. This mirrors a real provider's structured-output call (``client.messages.parse``), so
the moderation prompt + schema (in prompts.py / models.py) are written once and reused unchanged
by both implementations.

To add a real provider you implement exactly one method. Nothing else in the codebase changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResult:
    """What every LLMClient.classify call returns.

    ``parsed`` is the schema-validated model. ``raw_text`` is the underlying text the model
    produced (useful for debugging/auditing). ``usage`` carries token counts when a real provider
    reports them (None for the mock).
    """

    parsed: BaseModel
    raw_text: str
    usage: dict | None = None
    model: str = "mock"


class LLMClient(Protocol):
    """The seam. Implementations: MockLLMClient (offline) and AnthropicLLMClient (real Claude)."""

    def classify(self, system: str, user: str, schema: type[T]) -> LLMResult:
        """Run one structured-output call and return a validated ``schema`` instance."""
        ...

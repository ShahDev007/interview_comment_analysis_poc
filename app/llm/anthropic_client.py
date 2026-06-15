"""Real Claude implementation of the LLMClient seam.

This is the drop-in production path. It is NOT used by default -- the PoC runs entirely on the
mock with no API key. Set ``LLM_PROVIDER=anthropic`` (and ``ANTHROPIC_API_KEY``) to activate it.

Note how little is here: the prompt and the schema come from prompts.py / models.py unchanged.
The only provider-specific code is the SDK call. Swapping the model string (e.g. to
``claude-haiku-4-5`` for high-volume, cost-sensitive moderation) is a one-line change in config.
"""
from __future__ import annotations

from app.config import settings
from app.llm.base import LLMResult, T


class AnthropicLLMClient:
    """Implements LLMClient using the official Anthropic SDK and structured outputs."""

    def __init__(self, model: str | None = None):
        # Imported lazily so the package isn't required to run the mock.
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "The 'anthropic' package is required for LLM_PROVIDER=anthropic. "
                "Install it with: pip install anthropic"
            ) from exc

        # Anthropic() reads ANTHROPIC_API_KEY from the environment. We surface a clear error if
        # it's missing rather than failing deep inside an API call -- this is exactly the
        # 'seam check' described in the README.
        import os

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. The real LLM path needs only this key + this one "
                "method -- no other code changes. Set it, or run with LLM_PROVIDER=mock."
            )

        self._client = anthropic.Anthropic()
        self._model = model or settings.anthropic_model

    def classify(self, system: str, user: str, schema: type[T]) -> LLMResult:
        # messages.parse validates the model's JSON response straight into our Pydantic schema.
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
        usage = None
        if getattr(response, "usage", None) is not None:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        # content is a union of block types; only text blocks have .text -- use getattr so the
        # type checker doesn't have to narrow the whole union.
        raw_text = next(
            (getattr(b, "text", "") for b in response.content
             if getattr(b, "type", None) == "text"),
            "",
        )
        parsed = response.parsed_output
        if parsed is None:
            raise RuntimeError("Claude returned no parsed output for the classification schema.")
        return LLMResult(
            parsed=parsed,
            raw_text=raw_text,
            usage=usage,
            model=self._model,
        )

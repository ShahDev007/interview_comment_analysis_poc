"""Provider-agnostic moderation classifier.

Turns a Comment into a prompt, calls the LLMClient seam, and returns a validated
ClassificationResult. This layer is identical whether the seam is the mock or real Claude --
that's the whole point. It owns the prompt + schema; the client owns only the transport.
"""
from __future__ import annotations

from app.llm.base import LLMClient
from app.llm.prompts import SYSTEM_PROMPT, build_user_message
from app.models import ClassificationResult, Comment


class LLMModerationClassifier:
    def __init__(self, client: LLMClient):
        self._client = client

    def classify(self, comment: Comment) -> ClassificationResult:
        user = build_user_message(comment)
        # Embed the comment id as a hidden marker. The mock uses it to find a recorded fixture;
        # a real model simply ignores it. This keeps the LLMClient signature generic (system/user/
        # schema) without leaking moderation-specific arguments into the seam.
        user_with_marker = f"{user}\n\n__comment_id__:{comment.id}"
        result = self._client.classify(SYSTEM_PROMPT, user_with_marker, ClassificationResult)
        assert isinstance(result.parsed, ClassificationResult)
        return result.parsed

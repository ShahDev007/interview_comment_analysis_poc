"""Confidence + flags -> triage bucket.

The 'save time' story: high-confidence, clear cases auto-resolve so a human never sees them;
everything uncertain or sensitive is routed to a prioritized review queue.

Health-community safety rule: comments carrying ``always_review_flags`` (self_harm,
misinformation) are NEVER auto-actioned, regardless of confidence -- a human always decides.
"""
from __future__ import annotations

from app.config import settings
from app.models import ClassificationResult, Moderation, TriageBucket


def decide_triage(result: ClassificationResult) -> TriageBucket:
    has_sensitive_flag = any(f in settings.always_review_flags for f in result.flags)

    if has_sensitive_flag:
        return TriageBucket.NEEDS_REVIEW

    if result.moderation is Moderation.PASS:
        if result.moderation_confidence >= settings.auto_approve_threshold:
            return TriageBucket.AUTO_APPROVE
        return TriageBucket.NEEDS_REVIEW

    # moderation == Fail
    if result.moderation_confidence >= settings.auto_remove_threshold:
        return TriageBucket.AUTO_REMOVE
    return TriageBucket.NEEDS_REVIEW

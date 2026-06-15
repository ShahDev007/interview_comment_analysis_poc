"""Aggregate metrics for the dashboard KPI band.

The headline is estimated moderator time saved: auto-handled comments don't need a human, so each
saves ``seconds_per_comment`` (a stated assumption, configurable). We also report the LLM-vs-
baseline agreement rate -- low agreement is the visual proof that rules and AI diverge.
"""
from __future__ import annotations

from app.config import settings
from app.models import ClassifiedComment, Moderation, TriageBucket, UserType


def compute_metrics(classified: list[ClassifiedComment]) -> dict:
    total = len(classified)

    moderation_counts = {m.value: 0 for m in Moderation}
    user_type_counts = {u.value: 0 for u in UserType}
    triage_counts = {t.value: 0 for t in TriageBucket}
    disagreements = 0

    for c in classified:
        moderation_counts[c.llm.moderation.value] += 1
        user_type_counts[c.llm.user_type.value] += 1
        triage_counts[c.triage.value] += 1
        if c.disagreement:
            disagreements += 1

    auto_handled = triage_counts[TriageBucket.AUTO_APPROVE.value] + triage_counts[
        TriageBucket.AUTO_REMOVE.value
    ]
    needs_review = triage_counts[TriageBucket.NEEDS_REVIEW.value]

    seconds_saved = auto_handled * settings.seconds_per_comment
    agreement_rate = round(1 - (disagreements / total), 3) if total else 0.0

    return {
        "total": total,
        "moderation": moderation_counts,
        "user_type": user_type_counts,
        "triage": triage_counts,
        "auto_handled": auto_handled,
        "needs_review": needs_review,
        "auto_handled_pct": round(100 * auto_handled / total, 1) if total else 0.0,
        "disagreements": disagreements,
        "baseline_agreement_rate": agreement_rate,
        "seconds_per_comment_assumed": settings.seconds_per_comment,
        "estimated_seconds_saved": seconds_saved,
        "estimated_minutes_saved": round(seconds_saved / 60, 1),
    }

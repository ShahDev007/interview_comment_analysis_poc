"""Orchestration: load -> LLM classify + baseline -> triage -> cache.

Produces a list of ClassifiedComment. Results are cached to data/results.json so the dashboard is
snappy and re-runs are cheap; pass ``force=True`` to re-classify.
"""
from __future__ import annotations

import json

from app.classify.baseline import classify_baseline
from app.classify.llm_classifier import LLMModerationClassifier
from app.classify.triage import decide_triage
from app.config import RESULTS_CACHE_FILE
from app.data.loader import load_comments
from app.llm import get_llm_client
from app.models import ClassifiedComment


def classify_all(force: bool = False) -> list[ClassifiedComment]:
    """Run the full pipeline. Uses the cached results when available unless ``force``."""
    if not force and RESULTS_CACHE_FILE.exists():
        cached = _load_cache()
        if cached is not None:
            return cached

    comments = load_comments()
    classifier = LLMModerationClassifier(get_llm_client())

    classified: list[ClassifiedComment] = []
    for comment in comments:
        llm = classifier.classify(comment)
        baseline = classify_baseline(comment)
        triage = decide_triage(llm)
        disagreement = (
            llm.moderation is not baseline.moderation
            or llm.user_type is not baseline.user_type
        )
        confidence = min(llm.moderation_confidence, llm.user_type_confidence)
        classified.append(
            ClassifiedComment(
                comment=comment,
                llm=llm,
                baseline=baseline,
                triage=triage,
                disagreement=disagreement,
                confidence=confidence,
            )
        )

    _write_cache(classified)
    return classified


def _load_cache() -> list[ClassifiedComment] | None:
    try:
        raw = json.loads(RESULTS_CACHE_FILE.read_text(encoding="utf-8"))
        return [ClassifiedComment(**item) for item in raw]
    except Exception:
        return None


def _write_cache(classified: list[ClassifiedComment]) -> None:
    try:
        payload = [c.model_dump(mode="json") for c in classified]
        RESULTS_CACHE_FILE.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError:
        # Caching is a convenience, not a requirement -- never fail the pipeline over it.
        pass

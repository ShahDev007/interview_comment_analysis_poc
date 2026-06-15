"""Central configuration for the moderation PoC.

Everything that the business or a future deployment might want to tune lives here and is
overridable via environment variables, so the same code runs locally (mock) and hosted (real LLM)
with no edits. The ``LLM_PROVIDER`` seam is the headline: ``mock`` (default) runs fully offline;
``anthropic`` drops in a real Claude model with only an API key added.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Repo layout
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
# The dataset is read-only. We look for it in a few places so the app runs both standalone and
# when dropped into the interview repo (which keeps comments.json at the repo root). If none is
# present we fall back to the bundled sample so the PoC is always runnable. All are loaded
# identically by data/loader.py.
ROOT_COMMENTS_FILE = ROOT_DIR / "comments.json"      # interview repo's layout
COMMENTS_FILE = DATA_DIR / "comments.json"           # local layout
SAMPLE_COMMENTS_FILE = DATA_DIR / "sample_comments.json"
RESULTS_CACHE_FILE = DATA_DIR / "results.json"


def _get_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class Settings:
    # --- LLM seam ---------------------------------------------------------------------------
    # "mock" => MockLLMClient (offline, deterministic). "anthropic" => real Claude.
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "mock"))
    # Default to the most capable Claude model. For high-volume production moderation,
    # claude-haiku-4-5 or claude-sonnet-4-6 are cheaper one-line swaps (the seam is identical).
    anthropic_model: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
    )

    # --- Triage thresholds (confidence -> bucket) -------------------------------------------
    # A Pass at/above this confidence can be auto-approved without a human.
    auto_approve_threshold: float = field(
        default_factory=lambda: _get_float("AUTO_APPROVE_THRESHOLD", 0.85)
    )
    # A Fail at/above this confidence can be auto-removed -- UNLESS a serious flag is present
    # (in a health community we keep a human in the loop for those; see always_review_flags).
    auto_remove_threshold: float = field(
        default_factory=lambda: _get_float("AUTO_REMOVE_THRESHOLD", 0.90)
    )
    # Flags that always route to human review regardless of confidence. Self-harm and medical
    # misinformation carry real-world risk in a health community, so we never auto-action them.
    always_review_flags: tuple[str, ...] = ("self_harm", "misinformation")

    # --- Time-saved metric ------------------------------------------------------------------
    # Assumption (stated in the README): average seconds a human moderator spends per comment.
    # Auto-handled comments save this fully; needs-review comments still cost it.
    seconds_per_comment: float = field(
        default_factory=lambda: _get_float("SECONDS_PER_COMMENT", 30.0)
    )

    # Use bundled sample data if the real comments.json is absent.
    allow_sample_fallback: bool = field(
        default_factory=lambda: _get_bool("ALLOW_SAMPLE_FALLBACK", True)
    )

    def resolved_comments_file(self) -> Path:
        """Prefer the real dump (root, then data/); fall back to the bundled sample."""
        for candidate in (ROOT_COMMENTS_FILE, COMMENTS_FILE):
            if candidate.exists():
                return candidate
        if self.allow_sample_fallback and SAMPLE_COMMENTS_FILE.exists():
            return SAMPLE_COMMENTS_FILE
        return COMMENTS_FILE  # let the loader raise a clear error if none exists


settings = Settings()

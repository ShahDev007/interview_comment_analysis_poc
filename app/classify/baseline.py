"""The naive keyword/rules classifier -- the honest 'before AI' comparison.

This is deliberately simple and transparent: substring/keyword matching, the kind of rule a team
would write without an LLM. It exists so the dashboard can show concrete cases where it DISAGREES
with the LLM -- the core evidence for why AI is worth investing in. Its blind spots (missing the
prompt-injection in #104, the self-harm in #111, the PII in #113/119, the clinician-impersonation
scams, and roles like pharmacist/dietitian) are the point, not bugs to fix.
"""
from __future__ import annotations

import re

from app.models import BaselineResult, Comment, Moderation, UserType

# Banned/keyword lists a naive rules engine might use.
_BANNED = [
    "damn", "hell", "crap", "stupid", "idiot", "worthless", "pathetic",
    "cure", "big pharma", "no prescription", "click now", "% off",
    "stop taking", "ssn", "kill myself", "suicide", "essential oils",
    "blood pressure meds", "metformin", "oxy", "xanax",
]

_PROVIDER_TERMS = ["nurse", "doctor", "physician", "therapist", "rn", "clinician"]
_CAREGIVER_TERMS = ["my father", "my mother", "my dad", "my mom", "my son",
                    "my daughter", "looking after", "caring for"]
_PATIENT_TERMS = ["diagnosed", "my recovery", "my surgery", "my symptoms", "my numbers"]


def classify_baseline(comment: Comment) -> BaselineResult:
    text = comment.body.lower()

    # Banned terms use plain substring matching -- the brittle approach a naive profanity filter
    # actually uses (and the reason 'damn' Fails harmless venting).
    matched = [term for term in _BANNED if term in text]
    moderation = Moderation.FAIL if matched else Moderation.PASS

    # Role terms use word boundaries so short tokens like 'rn' don't match inside 'morning'.
    if _has_word(text, _PROVIDER_TERMS):
        user_type = UserType.HEALTHCARE_PROVIDER
    elif _has_word(text, _CAREGIVER_TERMS):
        user_type = UserType.CAREGIVER
    elif _has_word(text, _PATIENT_TERMS):
        user_type = UserType.PATIENT
    else:
        user_type = UserType.OTHER

    return BaselineResult(moderation=moderation, user_type=user_type, matched_terms=matched)


def _has_word(text: str, terms: list[str]) -> bool:
    """Match a term on word boundaries (so 'rn' won't fire inside 'morning')."""
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in terms)

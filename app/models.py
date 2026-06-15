"""Domain models shared across the whole pipeline.

``ClassificationResult`` is the contract the LLM must satisfy. It doubles as the JSON schema we
hand a real Claude structured-output call, so the prompt + schema are fully portable between the
mock and the real client -- that is the point of the seam.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Moderation(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"


class UserType(str, Enum):
    PATIENT = "Patient"
    CAREGIVER = "Caregiver"
    HEALTHCARE_PROVIDER = "Healthcare Provider"
    OTHER = "Other"


class TriageBucket(str, Enum):
    AUTO_APPROVE = "auto_approve"
    AUTO_REMOVE = "auto_remove"
    NEEDS_REVIEW = "needs_review"


class Comment(BaseModel):
    """A single piece of user-generated content. Loaded read-only from the dataset."""

    id: str
    body: str
    author: str | None = None
    post_title: str | None = None
    post_id: str | None = None
    timestamp: str | None = None


class ClassificationResult(BaseModel):
    """The structured output of *one* classification call (mock or real).

    This is intentionally provider-agnostic: a real Claude ``messages.parse`` call validates its
    JSON response straight into this model, and the mock client constructs the same shape.
    """

    moderation: Moderation
    moderation_reason: str = Field(description="Short rationale for the Pass/Fail decision.")
    moderation_confidence: float = Field(ge=0.0, le=1.0)
    user_type: UserType
    user_type_reason: str = Field(description="Short rationale for the user-type label.")
    user_type_confidence: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(
        default_factory=list,
        description="Policy flags, e.g. pii, misinformation, harassment, profanity, self_harm, spam.",
    )


class BaselineResult(BaseModel):
    """Output of the naive keyword/rules classifier -- the 'before AI' comparison."""

    moderation: Moderation
    user_type: UserType
    matched_terms: list[str] = Field(default_factory=list)


class ClassifiedComment(BaseModel):
    """A comment plus everything we computed about it: LLM result, baseline, triage decision."""

    comment: Comment
    llm: ClassificationResult
    baseline: BaselineResult
    triage: TriageBucket
    # True when LLM and keyword baseline disagree on moderation or user_type -- the headline
    # 'what rules miss' signal surfaced in the dashboard.
    disagreement: bool
    confidence: float = Field(description="Min of the two LLM confidences; drives triage + sort.")

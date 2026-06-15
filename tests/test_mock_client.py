"""Mock client: fixtures resolve, fallback works, results are deterministic."""
from app.llm.mock_client import MockLLMClient
from app.models import ClassificationResult, Moderation, UserType


def _classify(text_with_marker):
    client = MockLLMClient()
    return client.classify("sys", text_with_marker, ClassificationResult).parsed


def test_fixture_lookup_by_id():
    # 112 is recorded misinformation (stop insulin / 'cure').
    r = _classify("anything __comment_id__:112")
    assert r.moderation is Moderation.FAIL
    assert "misinformation" in r.flags


def test_deterministic():
    a = _classify("text __comment_id__:101")
    b = _classify("text __comment_id__:101")
    assert a.model_dump() == b.model_dump()


def test_heuristic_fallback_unknown_id():
    # No fixture for this id -> heuristic. 'no prescription' + 'buy' should flag spam.
    r = _classify("CHEAP MEDS no prescription, buy now __comment_id__:zzz999")
    assert r.moderation is Moderation.FAIL
    assert "spam" in r.flags


def test_heuristic_detects_provider():
    r = _classify("I'm a nurse and here is some advice __comment_id__:zzz998")
    assert r.user_type is UserType.HEALTHCARE_PROVIDER

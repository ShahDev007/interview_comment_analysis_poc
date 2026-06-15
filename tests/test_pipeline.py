"""End-to-end pipeline + metrics over the dataset."""
from app.classify.pipeline import classify_all
from app.metrics import compute_metrics


def test_pipeline_runs_and_metrics_shape():
    classified = classify_all(force=True)
    assert len(classified) >= 10

    m = compute_metrics(classified)
    assert m["total"] == len(classified)
    # Buckets and moderation counts sum to the total.
    assert sum(m["triage"].values()) == m["total"]
    assert sum(m["moderation"].values()) == m["total"]
    assert m["estimated_seconds_saved"] >= 0
    assert 0.0 <= m["baseline_agreement_rate"] <= 1.0


def test_dataset_has_disagreements():
    # The dataset is rich enough that the LLM and keyword baseline diverge on several comments;
    # that divergence is the whole 'why AI' argument.
    classified = classify_all(force=True)
    assert any(c.disagreement for c in classified)

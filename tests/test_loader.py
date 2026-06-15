"""Loader is schema-tolerant and read-only."""
import json

from app.data.loader import load_comments
from app.models import Comment


def test_loads_dataset():
    comments = load_comments()
    assert len(comments) >= 10
    assert all(isinstance(c, Comment) for c in comments)
    assert all(c.id and c.body for c in comments)


def test_tolerates_alternate_field_names(tmp_path):
    p = tmp_path / "alt.json"
    p.write_text(json.dumps([
        {"comment_id": "x1", "text": "hello", "username": "bob", "created_at": "2026-01-01"},
        {"_id": 7, "content": "world"},
    ]), encoding="utf-8")
    comments = load_comments(p)
    assert comments[0].id == "x1"
    assert comments[0].body == "hello"
    assert comments[0].author == "bob"
    assert comments[1].id == "7"
    assert comments[1].body == "world"


def test_tolerates_wrapper_object(tmp_path):
    p = tmp_path / "wrap.json"
    p.write_text(json.dumps({"comments": [{"id": "a", "body": "hi"}]}), encoding="utf-8")
    assert load_comments(p)[0].id == "a"


def test_maps_provided_schema(tmp_path):
    # The provided comments.json uses post_id/text/user_id and has no comment id.
    p = tmp_path / "real.json"
    p.write_text(json.dumps([
        {"post_id": 101, "user_id": "u_1", "text": "hi", "timestamp": "2026-06-15T10:00:00Z"},
    ]), encoding="utf-8")
    c = load_comments(p)[0]
    assert c.id == "101"
    assert c.author == "u_1"
    assert c.body == "hi"

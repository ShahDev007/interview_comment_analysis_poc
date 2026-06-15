"""Read-only loader for the comments dataset.

We don't assume the dataset's exact field names. The loader is deliberately tolerant: it accepts a
top-level list or a wrapped ``{"comments": [...]}`` object, and maps common field-name variants
onto our ``Comment`` model. The provided comments.json has no dedicated comment id (we fall back
to post_id), uses ``text`` for the body and ``user_id`` for the author.

This module NEVER writes to the dataset. (Results are cached separately by the pipeline.)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.models import Comment

# Field-name candidates, in priority order. Extend these once the real schema is known.
_ID_KEYS = ("id", "comment_id", "_id", "uuid", "post_id")
_BODY_KEYS = ("body", "text", "content", "comment", "message")
_AUTHOR_KEYS = ("author", "username", "user", "user_name", "display_name", "handle", "user_id")
_POST_TITLE_KEYS = ("post_title", "title", "thread_title", "post")
_POST_ID_KEYS = ("post_id", "thread_id", "topic_id")
_TIMESTAMP_KEYS = ("timestamp", "created_at", "date", "time", "createdAt")


def _first(record: dict[str, Any], keys: tuple[str, ...]) -> Optional[Any]:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _coerce(record: dict[str, Any], index: int) -> Comment:
    raw_id = _first(record, _ID_KEYS)
    return Comment(
        id=str(raw_id) if raw_id is not None else f"row-{index}",
        body=str(_first(record, _BODY_KEYS) or ""),
        author=_opt_str(_first(record, _AUTHOR_KEYS)),
        post_title=_opt_str(_first(record, _POST_TITLE_KEYS)),
        post_id=_opt_str(_first(record, _POST_ID_KEYS)),
        timestamp=_opt_str(_first(record, _TIMESTAMP_KEYS)),
    )


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def load_comments(path: Optional[Path] = None) -> list[Comment]:
    """Load and normalize comments from JSON. Read-only."""
    resolved = path or settings.resolved_comments_file()
    if not resolved.exists():
        raise FileNotFoundError(
            f"No dataset found at {resolved}. Drop the real comments.json into the repo root or "
            f"data/ directory, or keep the bundled sample_comments.json for the demo."
        )

    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        # Accept a wrapper like {"comments": [...]} or {"data": [...]}.
        for key in ("comments", "data", "items", "results"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            raise ValueError(
                f"Dataset at {resolved} is an object but has no list under "
                f"'comments'/'data'/'items'/'results'."
            )

    if not isinstance(raw, list):
        raise ValueError(f"Dataset at {resolved} is not a JSON list.")

    return [_coerce(rec, i) for i, rec in enumerate(raw) if isinstance(rec, dict)]

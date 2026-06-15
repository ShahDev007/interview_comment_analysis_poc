# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An LLM-assisted **comment-moderation proof of concept** for a health community. With read-only
access to `comments.json`, it classifies each comment on two axes — `moderation` (Pass/Fail) and
`user_type` (Patient/Caregiver/Healthcare Provider/Other) — with reasoning, confidence, a triage
decision, and a keyword-baseline comparison, surfaced in a FastAPI dashboard. All LLM calls are
**mocked** behind an interface; a real Claude model is a drop-in (env vars only).

## Commands

```bash
pip install -r requirements-dev.txt     # runtime + ruff/mypy (use requirements.txt for runtime only)
uvicorn app.main:app --reload           # run the dashboard at http://127.0.0.1:8000

python scripts/checks.py                # run ALL gates: build, lint, typecheck, test
python scripts/checks.py lint test      # run a subset
python -m pytest -q                     # tests only
python -m pytest -q -k triage           # a single test/group
python -m ruff check --fix app scripts  # lint + autofix
python -m mypy app                      # typecheck
```

- **build** = `python -m compileall app scripts` (no packaging step; catches syntax/import errors).
- **build** and **test** are *hard* gates; **lint** and **typecheck** are *advisory* (see hooks).
- Missing optional tools (ruff/mypy) are reported as SKIP, not failures.

## Architecture (the big picture)

Data flows one direction; the LLM is isolated behind a single seam.

```
comments.json (read-only)
  → app/data/loader.py          schema-tolerant load → Comment[]
  → app/classify/pipeline.py    orchestrates, caches to data/results.json
       ├ app/classify/llm_classifier.py   Comment → prompt → LLMClient → ClassificationResult
       │    └ app/llm/  THE SEAM: base.py (protocol) · mock_client.py (default) · anthropic_client.py
       ├ app/classify/baseline.py   naive keyword/rules — the \"before AI\" comparison
       ├ app/classify/triage.py     confidence + flags → bucket
       └ app/metrics.py             KPIs incl. time saved + baseline agreement
  → app/main.py (FastAPI)        /api/stats /api/comments /api/comments/{id} /api/classify
  → app/static/                  dashboard (vanilla JS + fetch, no build step)
```

### The LLM seam — the most important design point

`app/llm/base.py` defines `LLMClient`, a **generic** protocol
(`classify(system, user, schema) -> LLMResult`) that knows nothing about moderation. The
moderation prompt (`app/llm/prompts.py`) and output schema (`ClassificationResult` in
`app/models.py`) live one layer up in `LLMModerationClassifier` and are **shared unchanged** by
both implementations:

- `MockLLMClient` (default, offline, deterministic): recorded **fixtures** keyed by comment id
  (`app/llm/fixtures/responses.json`, the \"cassette\" pattern) + a heuristic fallback for unseen
  comments.
- `AnthropicLLMClient`: real Claude via `client.messages.parse(... output_format=...)`; documented
  but inactive by default.

Switching is **only** an env var — `get_llm_client()` in `app/llm/__init__.py` is the sole switch:

```bash
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uvicorn app.main:app
```

**When editing, preserve these invariants** (the `code-review`/`refactor`/`bug-fixer` agents
enforce them too):
- Keep `app/llm/base.py` provider-agnostic; never leak moderation logic into the seam.
- Keep prompt + schema shared between mock and real (no per-provider copies).
- `always_review_flags` (`self_harm`, `misinformation`) are **never** auto-actioned — always
  routed to human review regardless of confidence (`app/config.py`, `app/classify/triage.py`).
- The dataset is **read-only**; results cache to `data/results.json` (regenerate via
  `POST /api/classify`).

### Triage & config

Thresholds and the time-saved assumption live in `app/config.py` (env-overridable):
`AUTO_APPROVE_THRESHOLD` (0.85), `AUTO_REMOVE_THRESHOLD` (0.90), `SECONDS_PER_COMMENT` (30).
`MockLLMClient` resolves a fixture by a hidden `__comment_id__:<id>` marker that
`LLMModerationClassifier` appends to the user message — keep that marker if you touch either file.

### Dataset note

The provided `comments.json` has no dedicated comment id (the loader falls back to `post_id`), uses
`text` for the body and `user_id` for the author. `app/data/loader.py` is intentionally
schema-tolerant (accepts a list or a `{"comments": [...]}` wrapper and maps field-name variants) and
resolves the dataset from the repo root, then `data/`, then `data/sample_comments.json`. Fixture
keys `101`-`129` cover the provided data; `c001`-`c015` cover the sample.

## Claude Code tooling in this repo (`.claude/`)

**Hooks** (`.claude/settings.json`):
- `PostToolUse` on Edit/Write/MultiEdit → `scripts/hook_post_edit.py` quietly runs `ruff --fix` +
  `ruff format` on the edited `.py` file (non-blocking).
- `Stop` → `scripts/validate.py` is the **self-validation loop**: runs the checks and, if a hard
  gate (build/test) fails, blocks the stop with the failure report so Claude fixes its own mistakes
  and re-validates. It honors `stop_hook_active` to avoid infinite loops; lint/typecheck are
  advisory. Tune blocking gates with `VALIDATE_BLOCK_ON` (default `build,test`).

**Skills** (`.claude/skills/`): `quick-commit` (validate → stage → conventional commit),
`code-review` (review the diff against repo invariants), `tech-debt` (prioritized debt register).

**Agents** (`.claude/agents/`): `api-reviewer` (FastAPI surface), `bug-fixer` (reproduce → fix →
verify), `git-summarizer` (read-only diff/commit summaries), `refactor` (behavior-preserving
cleanups).

## Conventions

- Python 3.10+, type hints, Pydantic v2 models, `from __future__ import annotations`.
- Ruff (line length 100, rules E/W/F/I/B/UP) and mypy config are in `pyproject.toml`.
- Don't bypass hooks (no `--no-verify`); don't commit/push unless asked; never write to the dataset.
- After non-trivial changes, run `python scripts/checks.py` — the Stop hook will anyway.

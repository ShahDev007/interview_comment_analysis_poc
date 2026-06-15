---
name: tech-debt
description: Scan the codebase for technical debt (shortcuts, missing tests, fragile patterns, TODOs) and produce a prioritized, actionable register. Use when the user asks about tech debt, "what should we clean up", or wants a maintenance/hardening plan.
---

# tech-debt

Produce a technical-debt register for this repo -- a triage of what to fix and why it matters.

## How to scan
1. Grep for explicit markers: `TODO`, `FIXME`, `HACK`, `XXX`, `type: ignore`, `# noqa`.
2. Run `python scripts/checks.py` and capture lint/typecheck advisories -- each is a debt item.
3. Read the core modules (`app/llm/`, `app/classify/`, `app/main.py`, `app/data/loader.py`) and
   look for: missing tests on a branch, brittle assumptions, hard-coded values that should be
   config, error paths that swallow exceptions, and PoC shortcuts.

## This repo's known debt themes (check whether they still apply)
- **Mock realism vs. honesty** -- fixtures are hand-authored; note where the heuristic fallback is
  weak and what would need recording from a real model.
- **Schema tolerance** -- `loader.py` field mapping is heuristic; the provided comments.json lacks a
  true comment id (we fall back to `post_id`). Flag if a new dataset would break it.
- **Results cache** -- `data/results.json` has no invalidation on prompt/threshold changes.
- **Single-process state** -- the `lru_cache` of classified results in `app/main.py` won't refresh
  without `POST /api/classify`.
- **No auth / rate limiting** on the API (fine for a local PoC, debt for hosting).

## Output
A table: **Item | Location | Impact (High/Med/Low) | Effort (S/M/L) | Recommended fix**.
Sort by Impact then Effort. Keep it honest -- distinguish real risk from cosmetic nits. Do not fix
anything unless the user asks; this skill produces the plan.

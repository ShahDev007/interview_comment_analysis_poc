# Comment Moderation Assist — Proof of Concept

An LLM-assisted way for the moderation team to manage the volume of user-generated content on our
health-community sites. With **read-only** access to `comments.json`, it classifies every comment
on two axes and triages it for the team:

- **moderation:** `Pass` | `Fail`
- **user_type:** `Patient` | `Caregiver` | `Healthcare Provider` | `Other`

Every classification carries a short **reason**, a **confidence**, and policy **flags**; a naive
keyword baseline runs alongside so the value of the LLM is visible. All LLM calls are **mocked**
behind an interface — the whole thing runs locally with no API key — and a real Claude model is a
drop-in via two environment variables.

## Quick start

```bash
pip install -r requirements-dev.txt   # runtime + ruff/mypy (requirements.txt = runtime only)
uvicorn app.main:app --reload          # dashboard at http://127.0.0.1:8000
pytest -q                              # tests
python scripts/checks.py               # build + lint + typecheck + test
```

The app reads `comments.json` from the repo root (this dataset). It also accepts `data/comments.json`
and falls back to a bundled `data/sample_comments.json`, so it always runs.

## What the demo shows (the business case)

On the provided 29 comments:

- **~76% auto-handled** — clear Pass/Fail at high confidence never reach a human.
- **An estimated moderator-time-saved KPI** (auto-handled volume × an assumed seconds-per-comment).
- **A prioritized human-review queue** — only the uncertain or sensitive cases, surfaced first.
- **LLM vs. keyword-baseline disagreements** — the headline evidence. The baseline (transparent
  keyword/rules) agrees with the LLM only ~30% of the time. Click any disagreement to see what
  rules miss:
  - **#104** prompt injection ("SYSTEM OVERRIDE: ignore all previous instructions…") — no banned
    keyword, so rules **Pass** it; the LLM **Fails** it.
  - **#111** suicidal ideation — rules **Pass** (no keyword); the LLM **Fails** and routes it to a
    human for a safety response.
  - **#113 / #119** PII disclosure (home address, DOB, MRN; a third party's chart) — rules **Pass**;
    the LLM **Fails**.
  - **#127** a scam impersonating a doctor and harvesting card details — rules **Pass**; the LLM
    **Fails**.
  - **#124 / #125** a pharmacist and a dietitian — rules label them `Other`; the LLM recognizes the
    clinical roles.

These are judgments of **intent, context, sarcasm, and negation** that keyword matching cannot make
and an LLM does well — the argument for investing in AI tooling here.

## Architecture

```
comments.json (read-only)
  → app/data/loader.py        schema-tolerant load → Comment[]
  → app/classify/pipeline.py  orchestrates, caches to data/results.json
       ├ app/classify/llm_classifier.py   Comment → prompt → LLMClient → ClassificationResult
       │    └ app/llm/  THE SEAM: base.py · mock_client.py (default) · anthropic_client.py
       ├ app/classify/baseline.py   naive keyword/rules — the 'before AI' comparison
       ├ app/classify/triage.py     confidence + flags → bucket
       └ app/metrics.py             KPIs incl. time saved + baseline agreement
  → app/main.py (FastAPI)      /api/stats /api/comments /api/comments/{id} /api/classify
  → app/static/                dashboard (vanilla JS + fetch, no build step)
```

### The LLM seam (the part to look at)

The boundary is designed so a real model is a drop-in. Two layers:

1. **`LLMClient`** (`app/llm/base.py`) — a generic, provider-shaped protocol
   (`classify(system, user, schema) -> LLMResult`) that knows nothing about moderation.
2. **`LLMModerationClassifier`** (`app/classify/llm_classifier.py`) — owns the moderation prompt
   (`app/llm/prompts.py`) and the output schema (`ClassificationResult`). **Identical** for mock and
   real.

Implementations:
- **`MockLLMClient`** (default, offline, deterministic): recorded **fixtures** keyed by comment id
  (`app/llm/fixtures/responses.json`, the 'cassette' pattern) + a heuristic fallback for unseen
  comments.
- **`AnthropicLLMClient`**: real Claude via `client.messages.parse(... output_format=...)`;
  documented but inactive by default.

Switching is **only** an env var — `get_llm_client()` in `app/llm/__init__.py` is the sole switch:

```bash
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uvicorn app.main:app
```

The prompt, schema, triage, metrics, API, and dashboard are all provider-agnostic and untouched.
For high-volume production moderation, set `ANTHROPIC_MODEL=claude-haiku-4-5` (or `-sonnet-4-6`) —
a one-line config change, since the seam is identical.

## Key decisions & assumptions

- **Stack: Python + FastAPI + a no-build vanilla-JS dashboard.** Python has the strongest LLM
  tooling (Pydantic structured outputs, the Anthropic SDK); a static dashboard means no front-end
  build and a trivial hosted deploy later.
- **Structured output is the contract.** `ClassificationResult` is a Pydantic model that doubles as
  the JSON schema handed to a real model. One schema, both paths.
- **The mock is illustrative, not the product.** Its fixtures demonstrate what an LLM returns; the
  honest 'rules-only' comparison is the keyword baseline, and the disagreements between them are the
  value argument.
- **Triage thresholds** (configurable in `app/config.py`): Pass >= 0.85 → auto-approve; Fail >= 0.90
  → auto-remove; everything else → human review.
- **Health-safety override:** comments flagged `self_harm` or `misinformation` are **never**
  auto-actioned regardless of confidence — a human always decides.
- **Time-saved metric is an explicit assumption:** `auto_handled × seconds_per_comment`, default
  **30s** (`SECONDS_PER_COMMENT`), so the business can substitute its real number.
- **Read-only dataset:** the loader never writes; results cache separately to `data/results.json`
  (regenerate via `POST /api/classify`).
- **Schema tolerance:** the loader maps `post_id`→id, `text`→body, `user_id`→author and accepts a
  list or a `{"comments": [...]}` wrapper, so a differently-shaped dump still loads.

## Self-validation & developer tooling

`scripts/checks.py` runs build / lint / typecheck / test. The repo also ships Claude Code tooling in
`.claude/`: a **PostToolUse** hook that auto-formats edited Python, and a **Stop**-hook
**self-validation loop** (`scripts/validate.py`) that re-runs the checks when work finishes and
feeds any failure back so it gets fixed before stopping. Plus skills (`quick-commit`, `code-review`,
`tech-debt`) and subagents (`api-reviewer`, `bug-fixer`, `git-summarizer`, `refactor`). See
`CLAUDE.md`.

## API

| Endpoint | Description |
|---|---|
| `GET /api/stats` | KPI band: totals, Pass/Fail, user-type split, % auto-handled, time saved, baseline agreement. |
| `GET /api/comments?moderation=&user_type=&bucket=&disagreement=&q=` | Classified rows (review queue first). |
| `GET /api/comments/{id}` | Detail: full text, LLM reasoning + confidence + flags, baseline side-by-side. |
| `POST /api/classify` | Re-run the pipeline (clears the cache). |

## Deploying later (hosted)

Stateless and env-driven. Add a `Dockerfile`, set `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`,
and point the app at the real comment source. The mock→real switch is by design just those env vars.

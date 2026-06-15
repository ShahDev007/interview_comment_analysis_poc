---
name: code-review
description: Review the current diff (or named files) for correctness bugs and quality issues against this repo's conventions, then report findings by severity. Use when the user asks for a code review, "review my changes", or before a commit/PR.
---

# code-review

Review changes in this moderation-PoC repo and produce an actionable, prioritized report.

## Scope
- Default to the working diff: `git --no-pager diff` (and `--staged`). If the user names files or a
  PR, review those instead.
- Read the changed files in full for context, not just the hunks.

## What to look for (in priority order)
1. **Correctness bugs** -- wrong logic, off-by-one, mishandled `None`, broken control flow,
   incorrect Pydantic/enum usage, async/route bugs in `app/main.py`.
2. **The LLM seam invariants** -- changes must not leak moderation specifics into `app/llm/base.py`
   (the seam stays generic), and the prompt/schema must stay shared between mock and real clients.
   Flag anything that would make swapping `LLM_PROVIDER` require code changes.
3. **Moderation policy fidelity** -- triage thresholds, the `always_review_flags` safety override
   (self_harm / misinformation must never auto-action), and read-only access to the dataset.
4. **Reuse & simplification** -- duplicated logic, dead code, something a stdlib/existing helper
   already does.
5. **Tests** -- are new branches covered? Do fixtures/ids still line up with the dataset?

## Output
- Group findings as **Must-fix** / **Should-fix** / **Nice-to-have**, each with `file:line`, a
  one-line problem statement, and a concrete suggested change.
- End by running `python scripts/checks.py` and noting any failing gate.
- Be specific and concise. Do not rewrite the code unless asked -- recommend.

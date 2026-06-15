---
name: quick-commit
description: Stage and commit the current changes with a clear, conventional message after running the project checks. Use when the user says "commit", "quick commit", "save this", or wants changes committed.
---

# quick-commit

Create a single well-formed commit for the current working changes in this repo.

## Steps

1. **Validate first.** Run `python scripts/checks.py build test`. If a hard gate fails, stop and
   report the failure -- do **not** commit broken code. (Lint/typecheck are advisory; mention them
   but they don't block.)
2. **Inspect.** Run `git status --short` and `git --no-pager diff --staged` plus
   `git --no-pager diff` to see staged and unstaged changes. If nothing is changed, say so and stop.
3. **Branch check.** If on the default branch (`main`/`master`), ask before committing -- prefer a
   feature branch unless the user already said to commit here.
4. **Stage.** `git add -A` unless the user named specific paths.
5. **Message.** Write a Conventional-Commits subject (`feat:`, `fix:`, `refactor:`, `docs:`,
   `test:`, `chore:`) <= 72 chars, imperative mood, describing *what changed and why* -- not a file
   list. Add a short body only if the change isn't obvious. Reuse the `git-summarizer` agent's
   framing if the diff is large.
6. **Commit** with the message.
7. Report the resulting `git log -1 --oneline`.

## Rules
- Only commit when the user asked. Never push unless explicitly told.
- Never use `--no-verify` or skip hooks.
- One focused commit per logical change; if the diff spans unrelated changes, say so and propose
  splitting.

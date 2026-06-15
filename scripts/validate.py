"""Self-validation loop -- a Claude Code *Stop* hook.

When Claude finishes a turn, this runs the project's checks. If a hard gate (build or test) fails,
it blocks the stop with the failure report fed back to Claude, so Claude keeps working to fix its
own mistakes and re-validates -- a closed loop. Lint/typecheck are reported but advisory (they
don't trap the loop on style nits).

Loop-safety: Claude Code sets ``stop_hook_active: true`` on the stdin payload when it's already
continuing because of a previous Stop-hook block. We honor that: if it's set, we don't block again,
so the loop always terminates.

Hook contract used here (exit codes):
  - exit 0  -> allow the stop (checks pass, or already in a hook-driven continuation)
  - exit 2  -> block the stop; stderr is shown to Claude as the reason to keep going

Configure which gates hard-block via env VALIDATE_BLOCK_ON (default "build,test").
This script never raises: any internal error is swallowed and treated as "allow stop".
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.checks import render, run_all  # noqa: E402


def _read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def main() -> int:
    payload = _read_stdin_json()

    # Already continuing from a prior validation block -> don't re-block (prevents infinite loops).
    if payload.get("stop_hook_active"):
        return 0

    block_on = {g.strip() for g in os.environ.get("VALIDATE_BLOCK_ON", "build,test").split(",") if g.strip()}
    results = run_all()

    failures = [r for r in results if (not r.ok and not r.skipped and r.name in block_on)]
    advisories = [r for r in results if (not r.ok and not r.skipped and r.name not in block_on)]

    if not failures:
        # Surface advisory failures (lint/typecheck) without blocking.
        if advisories:
            print("Self-validation passed hard gates. Advisory issues remain:\n"
                  + render(advisories), file=sys.stderr)
        return 0

    report = render(results)
    print(
        "Self-validation FAILED. Fix these before finishing, then they will be re-checked:\n\n"
        + report
        + "\n\nRun `python scripts/checks.py` locally to reproduce.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # Never let the hook crash the session.
        raise SystemExit(0) from None

"""Auto-tidy hook -- a Claude Code *PostToolUse* hook for Edit/Write/MultiEdit.

After Claude edits a Python file, this quietly runs ruff's autofix + formatter on just that file,
so the working tree stays lint-clean without nagging Claude on every edit. Non-blocking: it always
exits 0 and never interrupts the flow. If ruff isn't installed, it's a no-op.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _edited_path(payload: dict) -> Path | None:
    tool_input = payload.get("tool_input") or {}
    fp = tool_input.get("file_path") or tool_input.get("path")
    if not fp:
        return None
    p = Path(fp)
    return p if p.suffix == ".py" and p.exists() else None


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    target = _edited_path(payload)
    if target is None:
        return 0

    import importlib.util

    if importlib.util.find_spec("ruff") is None:
        return 0

    for args in (["-m", "ruff", "check", "--fix", "-q", str(target)],
                 ["-m", "ruff", "format", "-q", str(target)]):
        try:
            subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=60)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

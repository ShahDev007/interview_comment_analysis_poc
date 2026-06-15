"""Project check runner: build, lint, typecheck, test.

One place that knows how to run each gate, used three ways:
  - manually:           python scripts/checks.py            (run all)
                        python scripts/checks.py lint test  (run a subset)
  - by the self-validation Stop hook (scripts/validate.py)
  - by the .claude skills/agents that need to verify their own work

Design notes:
  - Cross-platform: everything runs through ``sys.executable -m <tool>`` so it works on Windows.
  - Graceful degradation: if an optional tool (ruff, mypy) isn't installed, that gate is
    reported as SKIPPED rather than failing -- the loop stays useful on a bare checkout.
  - Pure-ish: ``run_all`` returns structured results; callers decide what to do with them.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_PATHS = ["app", "scripts"]


@dataclass
class CheckResult:
    name: str
    ok: bool
    skipped: bool
    output: str

    @property
    def status(self) -> str:
        if self.skipped:
            return "SKIP"
        return "PASS" if self.ok else "FAIL"


def _has_module(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _run(name: str, args: list[str], *, requires: str | None = None) -> CheckResult:
    if requires and not _has_module(requires):
        return CheckResult(name, ok=True, skipped=True,
                           output=f"{requires} not installed; skipped. (pip install -r requirements-dev.txt)")
    try:
        proc = subprocess.run(
            [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=300
        )
    except Exception as exc:  # pragma: no cover - defensive
        return CheckResult(name, ok=False, skipped=False, output=f"runner error: {exc}")
    out = (proc.stdout + proc.stderr).strip()
    return CheckResult(name, ok=proc.returncode == 0, skipped=False, output=out)


def run_build() -> CheckResult:
    # No packaging step for this app; compileall catches syntax/import errors fast.
    return _run("build", ["-m", "compileall", "-q", *APP_PATHS])


def run_lint() -> CheckResult:
    return _run("lint", ["-m", "ruff", "check", *APP_PATHS], requires="ruff")


def run_typecheck() -> CheckResult:
    return _run("typecheck", ["-m", "mypy", "app"], requires="mypy")


def run_test() -> CheckResult:
    return _run("test", ["-m", "pytest", "-q"], requires="pytest")


_GATES = {
    "build": run_build,
    "lint": run_lint,
    "typecheck": run_typecheck,
    "test": run_test,
}


def run_all(gates: list[str] | None = None) -> list[CheckResult]:
    selected = gates or list(_GATES)
    return [_GATES[g]() for g in selected if g in _GATES]


def render(results: list[CheckResult], *, verbose: bool = True) -> str:
    lines = []
    for r in results:
        lines.append(f"[{r.status:4}] {r.name}")
        if verbose and not r.ok and not r.skipped and r.output:
            lines.append("  " + r.output.replace("\n", "\n  "))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    gates = [a for a in argv if a in _GATES] or None
    if any(a in ("all", "-a", "--all") for a in argv):
        gates = None
    results = run_all(gates)
    print(render(results))
    # build/test are hard gates; lint/typecheck are advisory in CLI summary too.
    hard_fail = any((not r.ok and not r.skipped and r.name in ("build", "test")) for r in results)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

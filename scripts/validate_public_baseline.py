#!/usr/bin/env python3
"""Validate the committed public baseline slice."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "manifests" / "public_known_good_baseline.json"
REPORT_DIR = REPO_ROOT / "reports" / "out" / "public-known-good-baseline"


def require(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing expected artifact: {path}")


def main() -> int:
    plan = subprocess.run(
        ["python3", "scripts/public_baseline.py", "plan", "--manifest", str(MANIFEST)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    plan_doc = json.loads(plan.stdout)
    if plan_doc["run_id"] != "public-known-good-baseline":
        raise SystemExit("unexpected run_id in plan output")

    run_result = subprocess.run(
        ["python3", "scripts/public_baseline.py", "run", "--manifest", str(MANIFEST)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
    )
    if run_result.returncode not in (0, 2):
        raise SystemExit(f"unexpected baseline exit code: {run_result.returncode}")

    require(REPORT_DIR / "report.md")
    if run_result.returncode == 0:
        require(REPORT_DIR / "comparison" / "summary.json")
        require(REPORT_DIR / "comparison" / "summary.svg")
        return 0

    require(REPORT_DIR / "status.json")
    status = json.loads((REPORT_DIR / "status.json").read_text())
    if status.get("status") != "blocked":
        raise SystemExit("blocked baseline did not emit a blocked status")
    if sorted(status.get("missing_tools", [])) != ["ffmpeg", "ffprobe"]:
        raise SystemExit("blocked baseline did not report the expected missing tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

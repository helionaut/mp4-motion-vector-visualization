#!/usr/bin/env python3
"""Validate the committed public baseline slice."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "manifests" / "public-baseline.json"
REPORT_DIR = REPO_ROOT / "reports" / "out" / "public-baseline"


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
    if plan_doc["run_id"] != "public-baseline":
        raise SystemExit("unexpected run_id in plan output")
    require(REPORT_DIR / "status.json")
    require(REPORT_DIR / "report.md")
    status = json.loads((REPORT_DIR / "status.json").read_text())
    if status.get("status") not in {"blocked", "success"}:
        raise SystemExit("baseline status report must be either blocked or success")
    if status.get("status") == "success":
        require(REPORT_DIR / "comparison" / "summary.json")
        require(REPORT_DIR / "comparison" / "summary.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

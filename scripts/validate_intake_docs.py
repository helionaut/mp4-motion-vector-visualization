#!/usr/bin/env python3
"""Validate the planning docs required for the project intake lane."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_FILES = {
    "README.md": [
        "# mp4-motion-vector-visualization",
        "## Current planning entry points",
    ],
    "docs/PLAN.md": [
        "# Execution Plan",
        "## Goal",
        "## Execution Sequence",
        "## Issue Pack",
        "## First Next Actions",
    ],
    "docs/RESEARCH.md": [
        "# Research Contract",
        "## Strategic goal",
        "## Baseline hypothesis",
        "## Follow-up issue contract",
    ],
    "docs/ENVIRONMENT.md": [
        "# Environment Contract",
        "Default execution strategy: `docker`",
        "## Chosen strategy",
        "## Shared cache contract",
    ],
    "docs/INPUTS.md": [
        "# External Inputs Contract: MP4 Motion Vector Visualization",
        "## Source Inputs",
        "## Prepared Artifacts",
        "## Real Gaps",
    ],
}


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    missing: list[str] = []

    for relpath, required_snippets in REQUIRED_FILES.items():
        path = repo_root / relpath
        if not path.is_file():
            missing.append(f"{relpath}: file is missing")
            continue

        text = path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            if snippet not in text:
                missing.append(f"{relpath}: missing snippet {snippet!r}")

    if missing:
        for line in missing:
            print(line, file=sys.stderr)
        return 1

    print("Intake planning docs validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

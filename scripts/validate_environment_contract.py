#!/usr/bin/env python3
"""Validate the executable environment contract without requiring Docker."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


REQUIRED_FILES = {
    "Dockerfile": ["FROM debian:bookworm-slim", "ffmpeg", "python3", "tini"],
    "scripts/run_in_docker.sh": [
        "MMV_CACHE_ROOT",
        "doctor",
        "dry-run",
        "--volume \"${CACHE_ROOT}:/cache-root\"",
    ],
    "docs/ENVIRONMENT.md": [
        "## Chosen strategy",
        "`scripts/run_in_docker.sh`",
        "## Shared cache contract",
        "## Validation and handoff proof",
    ],
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    for relpath, required_snippets in REQUIRED_FILES.items():
        path = repo_root / relpath
        require(path.is_file(), f"{relpath}: file is missing", errors)
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            require(snippet in text, f"{relpath}: missing snippet {snippet!r}", errors)

    wrapper_path = repo_root / "scripts/run_in_docker.sh"
    if wrapper_path.is_file():
        mode = wrapper_path.stat().st_mode
        require(
            bool(mode & stat.S_IXUSR),
            "scripts/run_in_docker.sh: expected the wrapper to be executable",
            errors,
        )

        env = os.environ.copy()
        env["MMV_CACHE_ROOT"] = str(repo_root / ".tmp" / "research-cache")

        for subcommand in (
            ["doctor"],
            ["dry-run"],
            ["dry-run", "ffmpeg", "-version"],
            ["dry-run", "--", "ffmpeg", "-version"],
        ):
            result = subprocess.run(
                [str(wrapper_path), *subcommand],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            require(
                result.returncode == 0,
                f"scripts/run_in_docker.sh {' '.join(subcommand)}: returned {result.returncode}",
                errors,
            )
            output = result.stdout + result.stderr
            require("Cache root:" in output, f"scripts/run_in_docker.sh {' '.join(subcommand)}: missing cache summary", errors)

        dry_run = subprocess.run(
            [str(wrapper_path), "dry-run", "--", "ffmpeg", "-version"],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        dry_output = dry_run.stdout + dry_run.stderr
        require("docker build" in dry_output, "dry-run: missing docker build command", errors)
        require("docker run" in dry_output, "dry-run: missing docker run command", errors)
        require("/cache-root/downloads" in dry_output, "dry-run: missing cache mount environment", errors)

    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    print("Environment contract validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

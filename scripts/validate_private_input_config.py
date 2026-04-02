#!/usr/bin/env python3
"""Validate that the private input config points at real local MP4 files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_TOKENS = (
    "replace/with/",
    "replace-with-",
    "/path/to/",
    "example/",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def is_placeholder_path(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or any(token in normalized for token in PLACEHOLDER_TOKENS)


def find_missing_private_inputs(config: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    default_visibility = config.get("visibility", "private")

    for source in config.get("inputs", []):
        visibility = source.get("visibility", default_visibility)
        if visibility != "private":
            continue

        local_path = str(source.get("local_path", "")).strip()
        if is_placeholder_path(local_path):
            missing.append(
                {
                    "name": source.get("name", "<unnamed>"),
                    "reason": "placeholder-local-path",
                    "local_path": local_path,
                }
            )
            continue

        candidate = Path(local_path)
        if not candidate.is_file():
            missing.append(
                {
                    "name": source.get("name", "<unnamed>"),
                    "reason": "local-path-not-found",
                    "local_path": local_path,
                }
            )

    return missing


def write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to the private input config JSON.")
    parser.add_argument("--artifact", help="Optional blocker artifact path to update.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_json(config_path)
    missing_inputs = find_missing_private_inputs(config)

    if not missing_inputs:
        if args.artifact:
            write_artifact(
                Path(args.artifact),
                {
                    "status": "ready",
                    "current_step": "private inputs validated",
                    "config_path": str(config_path),
                    "missing_inputs": [],
                },
            )
        return 0

    payload = {
        "status": "blocked",
        "blocker": "missing-user-inputs",
        "current_step": "stage the real user MP4 pair referenced by the private config",
        "config_path": str(config_path),
        "missing_inputs": missing_inputs,
    }
    if args.artifact:
        write_artifact(Path(args.artifact), payload)

    json.dump(payload, sys.stderr, indent=2, sort_keys=True)
    sys.stderr.write("\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

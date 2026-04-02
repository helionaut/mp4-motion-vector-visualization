#!/usr/bin/env python3
"""Download, probe, and manifest MP4 comparison inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_CACHE_ROOT = Path("/home/helionaut/srv/research-cache/18afd661ce11")


@dataclass(frozen=True)
class Layout:
    datasets_root: Path
    public_raw_dir: Path
    public_prepared_dir: Path
    private_raw_dir: Path
    private_prepared_dir: Path


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_datasets_root(repo_root: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)

    research_context = repo_root / ".symphony" / "research-context.json"
    if research_context.is_file():
        return Path(load_json(research_context)["datasetsDir"])

    return Path(os.environ.get("MP4_MV_DATASETS_ROOT", DEFAULT_CACHE_ROOT / "datasets"))


def build_layout(datasets_root: Path, run_id: str) -> Layout:
    return Layout(
        datasets_root=datasets_root,
        public_raw_dir=datasets_root / "public" / "raw" / run_id,
        public_prepared_dir=datasets_root / "public" / "prepared" / run_id,
        private_raw_dir=datasets_root / "user" / "raw" / run_id,
        private_prepared_dir=datasets_root / "user" / "prepared" / run_id,
    )


def ensure_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_file(ffprobe_bin: str, input_path: Path) -> dict[str, Any]:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def summarize_probe(probe: dict[str, Any]) -> dict[str, Any]:
    video_stream = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"), {})
    format_info = probe.get("format", {})
    return {
        "container": format_info.get("format_name"),
        "duration_seconds": format_info.get("duration"),
        "bit_rate": format_info.get("bit_rate"),
        "size_bytes": format_info.get("size"),
        "video_codec": video_stream.get("codec_name"),
        "video_profile": video_stream.get("profile"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "pix_fmt": video_stream.get("pix_fmt"),
        "avg_frame_rate": video_stream.get("avg_frame_rate"),
        "audio_codec": audio_stream.get("codec_name"),
        "audio_channels": audio_stream.get("channels"),
        "audio_sample_rate": audio_stream.get("sample_rate"),
    }


def make_manifest(
    *,
    config: dict[str, Any],
    layout: Layout,
    ffprobe_bin: str,
    manifest_path: Path,
    generated_at: str,
) -> dict[str, Any]:
    prepared_probe_dir = layout.public_prepared_dir / "probe"
    prepared_probe_dir.mkdir(parents=True, exist_ok=True)

    inputs: list[dict[str, Any]] = []
    for source in config["inputs"]:
        raw_path = layout.public_raw_dir / source["filename"]
        ensure_file(source["source_url"], raw_path)
        probe = probe_file(ffprobe_bin, raw_path)
        probe_path = prepared_probe_dir / f"{source['name']}.ffprobe.json"
        probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        inputs.append(
            {
                "name": source["name"],
                "visibility": source["visibility"],
                "filename": source["filename"],
                "source_url": source["source_url"],
                "source_page_url": config["source_page_url"],
                "license_url": config["license_url"],
                "provenance": source["provenance"],
                "notes": source["notes"],
                "raw_path": str(raw_path),
                "raw_sha256": sha256sum(raw_path),
                "probe_path": str(probe_path),
                "probe_summary": summarize_probe(probe),
            }
        )

    return {
        "manifest_version": config["manifest_version"],
        "run_id": config["run_id"],
        "comparison_label": config["comparison_label"],
        "generated_at": generated_at,
        "visibility": config["visibility"],
        "tooling": {
            "ffprobe_bin": ffprobe_bin,
            "ffprobe_args": ["-v", "error", "-print_format", "json", "-show_format", "-show_streams"],
        },
        "paths": {
            "datasets_root": str(layout.datasets_root),
            "public_raw_dir": str(layout.public_raw_dir),
            "public_prepared_dir": str(layout.public_prepared_dir),
            "private_raw_dir": str(layout.private_raw_dir),
            "private_prepared_dir": str(layout.private_prepared_dir),
            "manifest_path": str(manifest_path),
            "vectors_dir": f"reports/out/{config['run_id']}/vectors",
            "renders_dir": f"reports/out/{config['run_id']}/renders",
            "comparison_dir": f"reports/out/{config['run_id']}/comparison",
        },
        "provenance": {
            "source_page_url": config["source_page_url"],
            "license_url": config["license_url"],
            "license_notes": config["license_notes"],
            "notes": config.get("notes", []),
        },
        "inputs": inputs,
        "private_input_contract": {
            "expected_raw_dir": str(layout.private_raw_dir),
            "expected_prepared_dir": str(layout.private_prepared_dir),
            "notes": [
                "HEL-152 should place user-provided MP4 files under the shared cache user/raw path for its run id.",
                "The same manifest shape can be reused once source_url fields are replaced by secure provenance notes."
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to the input set JSON config.")
    parser.add_argument("--manifest-out", required=True, help="Where to write the generated manifest JSON.")
    parser.add_argument("--ffprobe-bin", required=True, help="Path to the ffprobe binary.")
    parser.add_argument(
        "--datasets-root",
        help="Override the shared datasets root. Defaults to .symphony/research-context.json or the project cache.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    config_path = Path(args.config)
    manifest_path = Path(args.manifest_out)

    config = load_json(config_path)
    datasets_root = resolve_datasets_root(repo_root, args.datasets_root)
    layout = build_layout(datasets_root, config["run_id"])
    layout.public_raw_dir.mkdir(parents=True, exist_ok=True)
    layout.public_prepared_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = make_manifest(
        config=config,
        layout=layout,
        ffprobe_bin=args.ffprobe_bin,
        manifest_path=manifest_path,
        generated_at=generated_at,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

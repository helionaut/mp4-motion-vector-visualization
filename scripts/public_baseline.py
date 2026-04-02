#!/usr/bin/env python3
"""Run or plan the public known-good motion-vector baseline."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "public_known_good_baseline.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text())
    required_top_level = {"run_id", "inputs", "artifacts"}
    missing = required_top_level - set(data)
    if missing:
        raise ValueError(f"manifest missing required keys: {sorted(missing)}")
    if len(data["inputs"]) != 2:
        raise ValueError("manifest must define exactly two inputs")
    return data


def resolve_repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def build_generation_command(input_spec: dict[str, Any]) -> list[str]:
    generator = input_spec["generator"]
    output_path = resolve_repo_path(input_spec["relative_output_path"])
    return [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        generator["video_filter"],
        "-an",
        "-c:v",
        generator["codec"],
        "-pix_fmt",
        generator["pixel_format"],
        "-g",
        str(generator["gop_size"]),
        "-bf",
        str(generator["bf"]),
        "-r",
        str(generator["frame_rate"]),
        str(output_path),
    ]


def build_ffprobe_command(input_spec: dict[str, Any], output_path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-flags2",
        "+export_mvs",
        "-select_streams",
        "v:0",
        "-show_frames",
        "-show_entries",
        "frame=best_effort_timestamp_time,pict_type,side_data_list",
        "-of",
        "json",
        str(resolve_repo_path(input_spec["relative_output_path"])),
    ]


def build_render_command(input_spec: dict[str, Any], output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-flags2",
        "+export_mvs",
        "-i",
        str(resolve_repo_path(input_spec["relative_output_path"])),
        "-vf",
        "codecview=mv=pf+bf+bb,select='gte(n,1)'",
        "-frames:v",
        "1",
        str(output_path),
    ]


def summarize_ffprobe_frames(ffprobe_doc: dict[str, Any]) -> dict[str, Any]:
    frames = ffprobe_doc.get("frames", [])
    frame_summaries: list[dict[str, Any]] = []
    total_vectors = 0
    total_magnitude = 0.0
    frames_with_vectors = 0

    for index, frame in enumerate(frames):
        vectors: list[dict[str, Any]] = []
        for side_data in frame.get("side_data_list", []):
            if side_data.get("side_data_type") == "Motion vectors":
                vectors.extend(side_data.get("motion_vectors", []))

        vector_count = len(vectors)
        magnitude_sum = 0.0
        for vector in vectors:
            dx = float(vector["dst_x"]) - float(vector["src_x"])
            dy = float(vector["dst_y"]) - float(vector["src_y"])
            magnitude_sum += math.hypot(dx, dy)

        average_magnitude = magnitude_sum / vector_count if vector_count else 0.0
        frame_summary = {
            "frame_index": index,
            "timestamp": frame.get("best_effort_timestamp_time"),
            "pict_type": frame.get("pict_type"),
            "vector_count": vector_count,
            "average_magnitude": round(average_magnitude, 6),
        }
        frame_summaries.append(frame_summary)
        total_vectors += vector_count
        total_magnitude += magnitude_sum
        if vector_count:
            frames_with_vectors += 1

    mean_vector_magnitude = total_magnitude / total_vectors if total_vectors else 0.0
    return {
        "frame_count": len(frames),
        "frames_with_vectors": frames_with_vectors,
        "total_vectors": total_vectors,
        "mean_vector_magnitude": round(mean_vector_magnitude, 6),
        "frames": frame_summaries,
    }


def build_comparison_summary(per_input: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items = []
    for name, summary in per_input.items():
        items.append(
            {
                "name": name,
                "total_vectors": summary["total_vectors"],
                "mean_vector_magnitude": summary["mean_vector_magnitude"],
                "frames_with_vectors": summary["frames_with_vectors"],
                "frame_count": summary["frame_count"],
            }
        )

    if len(items) != 2:
        raise ValueError("comparison summary requires exactly two inputs")

    left, right = items
    vector_delta = left["total_vectors"] - right["total_vectors"]
    magnitude_delta = round(
        left["mean_vector_magnitude"] - right["mean_vector_magnitude"], 6
    )
    winner = left["name"] if left["total_vectors"] >= right["total_vectors"] else right["name"]

    return {
        "inputs": items,
        "delta": {
            "vector_count": vector_delta,
            "mean_vector_magnitude": magnitude_delta,
        },
        "higher_vector_count_input": winner,
    }


def build_comparison_svg(comparison_summary: dict[str, Any]) -> str:
    inputs = comparison_summary["inputs"]
    max_vectors = max(item["total_vectors"] for item in inputs) or 1
    max_magnitude = max(item["mean_vector_magnitude"] for item in inputs) or 1
    lines = [
        "<svg xmlns='http://www.w3.org/2000/svg' width='720' height='260' viewBox='0 0 720 260'>",
        "<rect width='720' height='260' fill='#f7f4ea' />",
        "<text x='32' y='40' font-family='monospace' font-size='20' fill='#1f2933'>Public Known-Good Baseline Comparison</text>",
    ]
    colors = ["#2563eb", "#dc2626"]
    for index, item in enumerate(inputs):
        bar_y = 70 + index * 90
        vector_width = int((item["total_vectors"] / max_vectors) * 280)
        magnitude_width = int((item["mean_vector_magnitude"] / max_magnitude) * 280)
        lines.extend(
            [
                f"<text x='32' y='{bar_y}' font-family='monospace' font-size='16' fill='#1f2933'>{item['name']}</text>",
                f"<rect x='240' y='{bar_y - 16}' width='{vector_width}' height='18' fill='{colors[index]}' />",
                f"<text x='530' y='{bar_y - 2}' font-family='monospace' font-size='13' fill='#1f2933'>vectors: {item['total_vectors']}</text>",
                f"<rect x='240' y='{bar_y + 14}' width='{magnitude_width}' height='18' fill='{colors[index]}' opacity='0.55' />",
                f"<text x='530' y='{bar_y + 28}' font-family='monospace' font-size='13' fill='#1f2933'>mean magnitude: {item['mean_vector_magnitude']}</text>",
            ]
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write_failure_report(manifest: dict[str, Any], missing_tools: list[str], report_dir: Path) -> Path:
    report = {
        "run_id": manifest["run_id"],
        "status": "blocked",
        "blocked_by": "missing-runtime-binaries",
        "missing_tools": missing_tools,
        "expected_command_surface": "scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run",
        "generated_at": utc_now(),
    }
    report_path = report_dir / "status.json"
    ensure_parent(report_path)
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    markdown_path = report_dir / "report.md"
    markdown_path.write_text(
        "\n".join(
            [
                "# Public Known-Good Baseline Report",
                "",
                f"- Run id: `{manifest['run_id']}`",
                "- Status: blocked on missing runtime binaries in the current host workspace",
                f"- Missing tools: `{', '.join(missing_tools)}`",
                "- Reproduction command once Docker is available:",
                "  `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json`",
                "",
                "This failure is expected on hosts without Docker and FFmpeg. The runner and manifest are committed so a future agent can rerun the same baseline without mixing in private media.",
                "",
            ]
        )
    )
    return report_path


def run_baseline(manifest: dict[str, Any]) -> int:
    artifact_paths = {name: resolve_repo_path(path) for name, path in manifest["artifacts"].items()}
    for path in artifact_paths.values():
        path.mkdir(parents=True, exist_ok=True)

    missing_tools = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing_tools:
        write_failure_report(manifest, missing_tools, artifact_paths["report_dir"])
        return 2

    per_input_summary: dict[str, dict[str, Any]] = {}
    command_log: list[dict[str, Any]] = []

    for input_spec in manifest["inputs"]:
        media_path = resolve_repo_path(input_spec["relative_output_path"])
        ensure_parent(media_path)
        generation_command = build_generation_command(input_spec)
        run_command(generation_command)
        command_log.append({"step": "generate", "input": input_spec["name"], "command": generation_command})

        ffprobe_output_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.ffprobe.json"
        ffprobe_command = build_ffprobe_command(input_spec, ffprobe_output_path)
        ffprobe_result = run_command(ffprobe_command, capture=True)
        ffprobe_output_path.write_text(ffprobe_result.stdout)
        command_log.append({"step": "extract", "input": input_spec["name"], "command": ffprobe_command})

        summary = summarize_ffprobe_frames(json.loads(ffprobe_result.stdout))
        summary["source_path"] = str(media_path.relative_to(REPO_ROOT))
        summary_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        per_input_summary[input_spec["name"]] = summary

        render_path = artifact_paths["renders_dir"] / f"{input_spec['name']}.png"
        render_command = build_render_command(input_spec, render_path)
        run_command(render_command)
        command_log.append({"step": "render", "input": input_spec["name"], "command": render_command})

    comparison_summary = build_comparison_summary(per_input_summary)
    comparison_summary["generated_at"] = utc_now()
    comparison_summary["command_log"] = command_log
    comparison_json_path = artifact_paths["comparison_dir"] / "summary.json"
    comparison_json_path.write_text(json.dumps(comparison_summary, indent=2) + "\n")

    comparison_svg_path = artifact_paths["comparison_dir"] / "summary.svg"
    comparison_svg_path.write_text(build_comparison_svg(comparison_summary))

    report_lines = [
        "# Public Known-Good Baseline Report",
        "",
        f"- Run id: `{manifest['run_id']}`",
        "- Status: success",
        "- Proven path: generated public fixtures -> ffprobe motion vectors -> codecview renders -> SVG comparison summary",
        "- Inputs:",
    ]
    for item in comparison_summary["inputs"]:
        report_lines.append(
            f"  - `{item['name']}`: {item['total_vectors']} vectors across {item['frames_with_vectors']}/{item['frame_count']} frames; mean magnitude {item['mean_vector_magnitude']}"
        )
    report_lines.extend(
        [
            "",
            f"- Higher vector-count input: `{comparison_summary['higher_vector_count_input']}`",
            f"- Comparison JSON: `{comparison_json_path.relative_to(REPO_ROOT)}`",
            f"- Comparison SVG: `{comparison_svg_path.relative_to(REPO_ROOT)}`",
            "",
        ]
    )
    report_path = artifact_paths["report_dir"] / "report.md"
    report_path.write_text("\n".join(report_lines) + "\n")
    return 0


def print_plan(manifest: dict[str, Any]) -> int:
    plan = {
        "run_id": manifest["run_id"],
        "wrapper_command": "scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json",
        "input_generation": {
            input_spec["name"]: build_generation_command(input_spec) for input_spec in manifest["inputs"]
        },
        "artifacts": manifest["artifacts"],
    }
    json.dump(plan, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("plan", "run"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    manifest = load_manifest(args.manifest)
    if args.command == "plan":
        return print_plan(manifest)
    return run_baseline(manifest)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run or plan the public motion-vector baseline."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "public-baseline.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text())
    required_top_level = {"run_id", "inputs", "paths", "tooling"}
    missing = required_top_level - set(data)
    if missing:
        raise ValueError(f"manifest missing required keys: {sorted(missing)}")
    if len(data["inputs"]) != 2:
        raise ValueError("manifest must define exactly two inputs")
    return data


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


def resolve_binary_paths(manifest: dict[str, Any]) -> tuple[Path, Path]:
    ffprobe_bin = Path(manifest["tooling"].get("ffprobe_bin", ""))
    ffmpeg_bin = ffprobe_bin.with_name("ffmpeg") if ffprobe_bin else Path()
    if ffprobe_bin.is_file() and ffmpeg_bin.is_file():
        return ffmpeg_bin, ffprobe_bin

    bootstrap_cmd = [str(REPO_ROOT / "scripts" / "bootstrap_media_tools.sh")]
    result = run_command(bootstrap_cmd, capture=True)
    ffprobe_bin = Path(result.stdout.strip())
    ffmpeg_bin = ffprobe_bin.with_name("ffmpeg")
    if not ffprobe_bin.is_file() or not ffmpeg_bin.is_file():
        raise FileNotFoundError(
            f"expected ffmpeg and ffprobe beside {ffprobe_bin}, but bootstrap did not produce them"
        )
    return ffmpeg_bin, ffprobe_bin


def build_ffprobe_command(ffprobe_bin: Path, input_spec: dict[str, Any]) -> list[str]:
    return [
        str(ffprobe_bin),
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
        input_spec["raw_path"],
    ]


def build_render_command(ffmpeg_bin: Path, input_spec: dict[str, Any], output_path: Path) -> list[str]:
    return [
        str(ffmpeg_bin),
        "-y",
        "-flags2",
        "+export_mvs",
        "-i",
        input_spec["raw_path"],
        "-vf",
        "codecview=mv=pf+bf+bb,select='gte(n,1)'",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(output_path),
    ]


def summarize_ffprobe_frames(ffprobe_doc: dict[str, Any]) -> dict[str, Any]:
    frames = ffprobe_doc.get("frames", [])
    frame_summaries: list[dict[str, Any]] = []
    total_vectors = 0
    total_magnitude = 0.0
    frames_with_vectors = 0
    frames_with_motion_side_data = 0

    for index, frame in enumerate(frames):
        vectors: list[dict[str, Any]] = []
        has_motion_side_data = False
        for side_data in frame.get("side_data_list", []):
            if side_data.get("side_data_type") == "Motion vectors":
                has_motion_side_data = True
                frames_with_motion_side_data += 1
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
            "motion_vector_side_data_present": has_motion_side_data,
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
        "frames_with_motion_side_data": frames_with_motion_side_data,
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
                "frames_with_motion_side_data": summary["frames_with_motion_side_data"],
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


def write_status_report(
    manifest: dict[str, Any],
    report_dir: Path,
    *,
    status: str,
    blocked_by: str | None = None,
    notes: list[str] | None = None,
    missing_tools: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> Path:
    report = {
        "run_id": manifest["run_id"],
        "status": status,
        "blocked_by": blocked_by,
        "missing_tools": missing_tools or [],
        "expected_command_surface": "scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json",
        "generated_at": utc_now(),
        "notes": notes or [],
        "details": details or {},
    }
    report_path = report_dir / "status.json"
    ensure_parent(report_path)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path = report_dir / "report.md"
    report_lines = [
        "# Public Baseline Report",
        "",
        f"- Run id: `{manifest['run_id']}`",
        f"- Status: {status}",
    ]
    if blocked_by:
        report_lines.append(f"- Blocked by: `{blocked_by}`")
    if missing_tools:
        report_lines.append(f"- Missing tools: `{', '.join(missing_tools)}`")
    report_lines.append(
        "- Command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`"
    )
    if notes:
        report_lines.append("- Notes:")
        for note in notes:
            report_lines.append(f"  - {note}")
    if details:
        report_lines.append("- Details:")
        for key, value in details.items():
            report_lines.append(f"  - `{key}`: `{json.dumps(value, sort_keys=True)}`")
    report_lines.append("")
    markdown_path.write_text("\n".join(report_lines) + "\n")
    return report_path


def run_baseline(manifest: dict[str, Any]) -> int:
    paths = manifest["paths"]
    artifact_paths = {
        "vectors_dir": REPO_ROOT / paths["vectors_dir"],
        "renders_dir": REPO_ROOT / paths["renders_dir"],
        "comparison_dir": REPO_ROOT / paths["comparison_dir"],
        "report_dir": REPO_ROOT / "reports" / "out" / manifest["run_id"],
    }
    for path in artifact_paths.values():
        path.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg_bin, ffprobe_bin = resolve_binary_paths(manifest)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        write_status_report(
            manifest,
            artifact_paths["report_dir"],
            status="blocked",
            blocked_by="ffmpeg-bootstrap-failed",
            notes=[str(exc)],
        )
        return 2

    per_input_summary: dict[str, dict[str, Any]] = {}
    command_log: list[dict[str, Any]] = []

    for input_spec in manifest["inputs"]:
        ffprobe_output_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.ffprobe.json"
        ffprobe_command = build_ffprobe_command(ffprobe_bin, input_spec)
        ffprobe_result = run_command(ffprobe_command, capture=True)
        ffprobe_output_path.write_text(ffprobe_result.stdout)
        command_log.append({"step": "extract", "input": input_spec["name"], "command": ffprobe_command})

        summary = summarize_ffprobe_frames(json.loads(ffprobe_result.stdout))
        summary["source_path"] = input_spec["raw_path"]
        summary["raw_sha256"] = input_spec.get("raw_sha256")
        summary_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        per_input_summary[input_spec["name"]] = summary

        render_path = artifact_paths["renders_dir"] / f"{input_spec['name']}.png"
        render_command = build_render_command(ffmpeg_bin, input_spec, render_path)
        run_command(render_command)
        command_log.append({"step": "render", "input": input_spec["name"], "command": render_command})

    if sum(item["total_vectors"] for item in per_input_summary.values()) == 0:
        had_motion_side_data = any(
            item["frames_with_motion_side_data"] > 0 for item in per_input_summary.values()
        )
        write_status_report(
            manifest,
            artifact_paths["report_dir"],
            status="blocked",
            blocked_by="motion-vector-payload-missing" if had_motion_side_data else "motion-vectors-not-exported",
            notes=[
                "ffprobe completed for both public MP4 inputs",
                "codecview render artifacts were written",
                (
                    "motion-vector side-data markers are present, but the ffprobe JSON payload does not include coordinate arrays"
                    if had_motion_side_data
                    else "no motion-vector side-data markers were exported for either public MP4 input"
                ),
            ],
            details={
                name: {
                    "frame_count": summary["frame_count"],
                    "frames_with_motion_side_data": summary["frames_with_motion_side_data"],
                    "frames_with_vectors": summary["frames_with_vectors"],
                    "total_vectors": summary["total_vectors"],
                }
                for name, summary in per_input_summary.items()
            },
        )
        return 3

    comparison_summary = build_comparison_summary(per_input_summary)
    comparison_summary["generated_at"] = utc_now()
    comparison_summary["command_log"] = command_log
    comparison_json_path = artifact_paths["comparison_dir"] / "summary.json"
    comparison_json_path.write_text(json.dumps(comparison_summary, indent=2) + "\n")

    comparison_svg_path = artifact_paths["comparison_dir"] / "summary.svg"
    comparison_svg_path.write_text(build_comparison_svg(comparison_summary))

    status_path = write_status_report(
        manifest,
        artifact_paths["report_dir"],
        status="success",
        notes=[
            "public baseline extraction completed from the prepared HEL-150 manifest",
            f"ffmpeg bin: {ffmpeg_bin}",
            f"ffprobe bin: {ffprobe_bin}",
        ],
    )

    report_lines = [
        "# Public Baseline Report",
        "",
        f"- Run id: `{manifest['run_id']}`",
        "- Status: success",
        "- Proven path: prepared public MP4 manifest -> ffprobe motion vectors -> codecview renders -> SVG comparison summary",
        f"- Input manifest: `{Path(paths['manifest_path']).name}`",
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
            f"- Status JSON: `{status_path.relative_to(REPO_ROOT)}`",
            "",
        ]
    )
    report_path = artifact_paths["report_dir"] / "report.md"
    report_path.write_text("\n".join(report_lines) + "\n")
    return 0


def print_plan(manifest: dict[str, Any]) -> int:
    plan = {
        "run_id": manifest["run_id"],
        "prepare_command": "scripts/prepare_public_inputs.sh",
        "run_command": "python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json",
        "inputs": [
            {
                "name": input_spec["name"],
                "raw_path": input_spec["raw_path"],
                "source_url": input_spec["source_url"],
            }
            for input_spec in manifest["inputs"]
        ],
        "artifacts": {
            "vectors_dir": manifest["paths"]["vectors_dir"],
            "renders_dir": manifest["paths"]["renders_dir"],
            "comparison_dir": manifest["paths"]["comparison_dir"],
        },
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

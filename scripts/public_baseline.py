#!/usr/bin/env python3
"""Run or plan the public motion-vector baseline."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "public-baseline.json"
DEFAULT_PROGRESS_ARTIFACT = REPO_ROOT / ".symphony" / "progress" / "HEL-155.json"
FRAME_LINE_RE = re.compile(r"n:\s*(\d+).*?\btype:([A-Z])\b")
MOTION_VECTOR_BYTES_RE = re.compile(r"side data - Motion vectors: \((\d+) bytes\)")


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


def write_progress_artifact(
    progress_path: Path,
    *,
    status: str,
    current_step: str,
    completed: int | None = None,
    total: int | None = None,
    unit: str = "frames",
    rate: float | None = None,
    eta_seconds: float | None = None,
    metrics: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> None:
    ensure_parent(progress_path)
    progress: dict[str, Any] = {
        "status": status,
        "current_step": current_step,
        "updated_at": utc_now(),
        "unit": unit,
        "metrics": metrics or {},
        "artifacts": artifacts or {},
    }
    if completed is not None:
        progress["completed"] = completed
    if total is not None:
        progress["total"] = total
        if total:
            progress["progress_percent"] = round((completed or 0) / total * 100, 2)
    if rate is not None:
        progress["rate"] = round(rate, 6)
    if eta_seconds is not None:
        progress["eta_seconds"] = round(eta_seconds, 3)
    progress_path.write_text(json.dumps(progress, indent=2) + "\n")


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


def build_extract_command(ffmpeg_bin: Path, input_spec: dict[str, Any]) -> list[str]:
    return [
        str(ffmpeg_bin),
        "-hide_banner",
        "-export_side_data",
        "+mvs",
        "-i",
        input_spec["raw_path"],
        "-an",
        "-vf",
        "showinfo",
        "-f",
        "null",
        "-",
    ]


def build_render_command(ffmpeg_bin: Path, input_spec: dict[str, Any], output_path: Path) -> list[str]:
    return [
        str(ffmpeg_bin),
        "-y",
        "-export_side_data",
        "+mvs",
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


def summarize_ffmpeg_showinfo(log_text: str) -> dict[str, Any]:
    frame_summaries: list[dict[str, Any]] = []
    current_frame: dict[str, Any] | None = None
    total_motion_vector_payload_bytes = 0
    frames_with_motion_side_data = 0
    max_motion_vector_payload_bytes = 0

    for line in log_text.splitlines():
        frame_match = FRAME_LINE_RE.search(line)
        if frame_match:
            current_frame = {
                "frame_index": int(frame_match.group(1)),
                "pict_type": frame_match.group(2),
                "motion_vector_side_data_present": False,
                "motion_vector_payload_bytes": 0,
                "vector_count": 0,
            }
            frame_summaries.append(current_frame)
            continue

        payload_match = MOTION_VECTOR_BYTES_RE.search(line)
        if payload_match and current_frame is not None:
            payload_bytes = int(payload_match.group(1))
            current_frame["motion_vector_side_data_present"] = True
            current_frame["motion_vector_payload_bytes"] = payload_bytes
            total_motion_vector_payload_bytes += payload_bytes
            frames_with_motion_side_data += 1
            max_motion_vector_payload_bytes = max(max_motion_vector_payload_bytes, payload_bytes)

    mean_payload_bytes = (
        total_motion_vector_payload_bytes / frames_with_motion_side_data
        if frames_with_motion_side_data
        else 0.0
    )
    return {
        "extractor_surface": "ffmpeg -export_side_data +mvs -vf showinfo",
        "frame_count": len(frame_summaries),
        "frames_with_vectors": 0,
        "frames_with_motion_side_data": frames_with_motion_side_data,
        "total_vectors": 0,
        "mean_vector_magnitude": 0.0,
        "coordinate_vectors_available": False,
        "total_motion_vector_payload_bytes": total_motion_vector_payload_bytes,
        "mean_motion_vector_payload_bytes": round(mean_payload_bytes, 6),
        "max_motion_vector_payload_bytes": max_motion_vector_payload_bytes,
        "frames": frame_summaries,
    }


def estimate_input_frame_count(input_spec: dict[str, Any]) -> int | None:
    probe_summary = input_spec.get("probe_summary") or {}
    avg_frame_rate = probe_summary.get("avg_frame_rate")
    duration_seconds = probe_summary.get("duration_seconds")
    if not avg_frame_rate or not duration_seconds:
        return None
    try:
        numerator, denominator = avg_frame_rate.split("/", 1)
        fps = float(numerator) / float(denominator)
        duration = float(duration_seconds)
    except (ValueError, ZeroDivisionError):
        return None
    return max(1, round(fps * duration))


def run_extract_command(
    command: list[str],
    *,
    log_path: Path,
    progress_path: Path,
    input_name: str,
    processed_frames_before: int,
    total_frames: int | None,
    artifacts: dict[str, Any],
) -> str:
    ensure_parent(log_path)
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    lines: list[str] = []
    decoded_frames = 0
    try:
        assert process.stderr is not None
        for raw_line in process.stderr:
            lines.append(raw_line)
            frame_match = FRAME_LINE_RE.search(raw_line)
            if frame_match:
                decoded_frames = max(decoded_frames, int(frame_match.group(1)) + 1)
                completed = processed_frames_before + decoded_frames
                write_progress_artifact(
                    progress_path,
                    status="running",
                    current_step=f"extracting {input_name} with ffmpeg -export_side_data +mvs",
                    completed=completed,
                    total=total_frames,
                    metrics={
                        "input": input_name,
                        "decoded_frames_current_input": decoded_frames,
                    },
                    artifacts=artifacts,
                )
    finally:
        return_code = process.wait()

    log_text = "".join(lines)
    log_path.write_text(log_text)
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    return log_text


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
                "total_motion_vector_payload_bytes": summary.get("total_motion_vector_payload_bytes", 0),
                "mean_motion_vector_payload_bytes": summary.get("mean_motion_vector_payload_bytes", 0.0),
            }
        )

    if len(items) != 2:
        raise ValueError("comparison summary requires exactly two inputs")

    left, right = items
    vector_delta = left["total_vectors"] - right["total_vectors"]
    magnitude_delta = round(
        left["mean_vector_magnitude"] - right["mean_vector_magnitude"], 6
    )
    payload_delta = left["total_motion_vector_payload_bytes"] - right["total_motion_vector_payload_bytes"]
    winner = (
        left["name"]
        if left["total_motion_vector_payload_bytes"] >= right["total_motion_vector_payload_bytes"]
        else right["name"]
    )

    return {
        "inputs": items,
        "delta": {
            "vector_count": vector_delta,
            "mean_vector_magnitude": magnitude_delta,
            "motion_vector_payload_bytes": payload_delta,
        },
        "higher_motion_vector_payload_input": winner,
    }


def build_comparison_svg(comparison_summary: dict[str, Any]) -> str:
    inputs = comparison_summary["inputs"]
    max_payload_bytes = max(item["total_motion_vector_payload_bytes"] for item in inputs) or 1
    max_side_data_frames = max(item["frames_with_motion_side_data"] for item in inputs) or 1
    lines = [
        "<svg xmlns='http://www.w3.org/2000/svg' width='720' height='260' viewBox='0 0 720 260'>",
        "<rect width='720' height='260' fill='#f7f4ea' />",
        "<text x='32' y='40' font-family='monospace' font-size='20' fill='#1f2933'>FFmpeg export_side_data MVS Comparison</text>",
    ]
    colors = ["#2563eb", "#dc2626"]
    for index, item in enumerate(inputs):
        bar_y = 70 + index * 90
        payload_width = int((item["total_motion_vector_payload_bytes"] / max_payload_bytes) * 280)
        frame_width = int((item["frames_with_motion_side_data"] / max_side_data_frames) * 280)
        lines.extend(
            [
                f"<text x='32' y='{bar_y}' font-family='monospace' font-size='16' fill='#1f2933'>{item['name']}</text>",
                f"<rect x='240' y='{bar_y - 16}' width='{payload_width}' height='18' fill='{colors[index]}' />",
                f"<text x='530' y='{bar_y - 2}' font-family='monospace' font-size='13' fill='#1f2933'>mv bytes: {item['total_motion_vector_payload_bytes']}</text>",
                f"<rect x='240' y='{bar_y + 14}' width='{frame_width}' height='18' fill='{colors[index]}' opacity='0.55' />",
                f"<text x='530' y='{bar_y + 28}' font-family='monospace' font-size='13' fill='#1f2933'>frames w/ mv side data: {item['frames_with_motion_side_data']}</text>",
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
        "expected_command_surface": "scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json",
        "docker_command_surface": "scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json",
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
        "- Host command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`"
    )
    report_lines.append(
        "- Docker command surface: `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`"
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


def run_baseline(manifest: dict[str, Any], *, progress_artifact: Path) -> int:
    paths = manifest["paths"]
    artifact_paths = {
        "vectors_dir": REPO_ROOT / paths["vectors_dir"],
        "renders_dir": REPO_ROOT / paths["renders_dir"],
        "comparison_dir": REPO_ROOT / paths["comparison_dir"],
        "report_dir": REPO_ROOT / "reports" / "out" / manifest["run_id"],
    }
    for path in artifact_paths.values():
        path.mkdir(parents=True, exist_ok=True)
    estimated_total_frames = sum(
        estimate_input_frame_count(input_spec) or 0 for input_spec in manifest["inputs"]
    ) or None
    shared_artifacts = {
        "report_dir": str(artifact_paths["report_dir"].relative_to(REPO_ROOT)),
        "vectors_dir": str(artifact_paths["vectors_dir"].relative_to(REPO_ROOT)),
        "renders_dir": str(artifact_paths["renders_dir"].relative_to(REPO_ROOT)),
        "comparison_dir": str(artifact_paths["comparison_dir"].relative_to(REPO_ROOT)),
    }
    write_progress_artifact(
        progress_artifact,
        status="starting",
        current_step="resolving ffmpeg tooling for the public baseline rerun",
        completed=0,
        total=estimated_total_frames,
        metrics={"inputs_total": len(manifest["inputs"])},
        artifacts=shared_artifacts,
    )

    try:
        ffmpeg_bin, ffprobe_bin = resolve_binary_paths(manifest)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        write_progress_artifact(
            progress_artifact,
            status="blocked",
            current_step="ffmpeg bootstrap failed",
            completed=0,
            total=estimated_total_frames,
            metrics={"error": str(exc)},
            artifacts=shared_artifacts,
        )
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
    processed_frames = 0

    for index, input_spec in enumerate(manifest["inputs"], start=1):
        extract_log_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.ffmpeg-showinfo.log"
        extract_command = build_extract_command(ffmpeg_bin, input_spec)
        command_log.append({"step": "extract", "input": input_spec["name"], "command": extract_command})
        log_text = run_extract_command(
            extract_command,
            log_path=extract_log_path,
            progress_path=progress_artifact,
            input_name=input_spec["name"],
            processed_frames_before=processed_frames,
            total_frames=estimated_total_frames,
            artifacts=shared_artifacts,
        )
        summary = summarize_ffmpeg_showinfo(log_text)
        summary["source_path"] = input_spec["raw_path"]
        summary["raw_sha256"] = input_spec.get("raw_sha256")
        summary["showinfo_log"] = str(extract_log_path.relative_to(REPO_ROOT))
        summary_path = artifact_paths["vectors_dir"] / f"{input_spec['name']}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        per_input_summary[input_spec["name"]] = summary
        processed_frames += summary["frame_count"]
        write_progress_artifact(
            progress_artifact,
            status="running",
            current_step=f"rendering codecview output for {input_spec['name']} ({index}/{len(manifest['inputs'])})",
            completed=processed_frames,
            total=estimated_total_frames,
            metrics={
                "input": input_spec["name"],
                "frames_processed": processed_frames,
                "frames_with_motion_side_data": summary["frames_with_motion_side_data"],
                "motion_vector_payload_bytes": summary["total_motion_vector_payload_bytes"],
            },
            artifacts=shared_artifacts,
        )

        render_path = artifact_paths["renders_dir"] / f"{input_spec['name']}.png"
        render_command = build_render_command(ffmpeg_bin, input_spec, render_path)
        run_command(render_command)
        command_log.append({"step": "render", "input": input_spec["name"], "command": render_command})

    if sum(item["total_vectors"] for item in per_input_summary.values()) == 0:
        had_motion_side_data = any(item["frames_with_motion_side_data"] > 0 for item in per_input_summary.values())
        had_motion_vector_payload_bytes = any(
            item["total_motion_vector_payload_bytes"] > 0 for item in per_input_summary.values()
        )
        blocked_by = "ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors"
        if not had_motion_side_data:
            blocked_by = "ffmpeg-export-side-data-mvs-no-side-data"
        elif not had_motion_vector_payload_bytes:
            blocked_by = "ffmpeg-export-side-data-mvs-zero-payload-bytes"
        comparison_summary = build_comparison_summary(per_input_summary)
        comparison_summary["generated_at"] = utc_now()
        comparison_summary["command_log"] = command_log
        comparison_json_path = artifact_paths["comparison_dir"] / "summary.json"
        comparison_json_path.write_text(json.dumps(comparison_summary, indent=2) + "\n")
        comparison_svg_path = artifact_paths["comparison_dir"] / "summary.svg"
        comparison_svg_path.write_text(build_comparison_svg(comparison_summary))
        write_progress_artifact(
            progress_artifact,
            status="blocked",
            current_step="ffmpeg decode path finished without coordinate-bearing vectors",
            completed=processed_frames,
            total=estimated_total_frames,
            metrics={
                "inputs_total": len(manifest["inputs"]),
                "frames_with_motion_side_data": sum(
                    item["frames_with_motion_side_data"] for item in per_input_summary.values()
                ),
                "motion_vector_payload_bytes": sum(
                    item["total_motion_vector_payload_bytes"] for item in per_input_summary.values()
                ),
                "coordinate_vectors_available": False,
            },
            artifacts={
                **shared_artifacts,
                "comparison_json": str(comparison_json_path.relative_to(REPO_ROOT)),
                "comparison_svg": str(comparison_svg_path.relative_to(REPO_ROOT)),
            },
        )
        write_status_report(
            manifest,
            artifact_paths["report_dir"],
            status="blocked",
            blocked_by=blocked_by,
            notes=[
                "ffmpeg decode-path extraction completed for both public MP4 inputs",
                "codecview render artifacts were written",
                (
                    "motion-vector side-data bytes are present on the FFmpeg decode path, but the CLI still does not serialize coordinate-bearing vectors"
                    if had_motion_vector_payload_bytes
                    else (
                        "motion-vector side-data markers are present, but the decode path reported zero payload bytes"
                        if had_motion_side_data
                        else "no motion-vector side-data markers were exported for either public MP4 input on the decode path"
                    )
                ),
            ],
            details={
                name: {
                    "frame_count": summary["frame_count"],
                    "frames_with_motion_side_data": summary["frames_with_motion_side_data"],
                    "frames_with_vectors": summary["frames_with_vectors"],
                    "total_vectors": summary["total_vectors"],
                    "total_motion_vector_payload_bytes": summary["total_motion_vector_payload_bytes"],
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
    write_progress_artifact(
        progress_artifact,
        status="success",
        current_step="public baseline extraction and comparison completed",
        completed=processed_frames,
        total=estimated_total_frames,
        metrics={
            "inputs_total": len(manifest["inputs"]),
            "total_vectors": sum(item["total_vectors"] for item in per_input_summary.values()),
        },
        artifacts={
            **shared_artifacts,
            "comparison_json": str(comparison_json_path.relative_to(REPO_ROOT)),
            "comparison_svg": str(comparison_svg_path.relative_to(REPO_ROOT)),
        },
    )

    report_lines = [
        "# Public Baseline Report",
        "",
        f"- Run id: `{manifest['run_id']}`",
        "- Status: success",
        "- Proven path: prepared public MP4 manifest -> ffmpeg -export_side_data +mvs decode path -> codecview renders -> SVG comparison summary",
        f"- Input manifest: `{Path(paths['manifest_path']).name}`",
        "- Inputs:",
    ]
    for item in comparison_summary["inputs"]:
        report_lines.append(
            f"  - `{item['name']}`: {item['total_motion_vector_payload_bytes']} motion-vector bytes across {item['frames_with_motion_side_data']}/{item['frame_count']} frames"
        )
    report_lines.extend(
        [
            "",
            f"- Higher motion-vector payload input: `{comparison_summary['higher_motion_vector_payload_input']}`",
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
        "run_command": "python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json",
        "docker_run_command": "scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json",
        "extractor_surface": "ffmpeg -export_side_data +mvs -vf showinfo",
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
        if name == "run":
            subparser.add_argument("--progress-artifact", type=Path, default=DEFAULT_PROGRESS_ARTIFACT)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    manifest = load_manifest(args.manifest)
    if args.command == "plan":
        return print_plan(manifest)
    return run_baseline(manifest, progress_artifact=args.progress_artifact)


if __name__ == "__main__":
    raise SystemExit(main())

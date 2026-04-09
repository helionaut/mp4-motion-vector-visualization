#!/usr/bin/env python3
"""Render a dense optical-flow-style map from codec motion vectors."""

from __future__ import annotations

import argparse
import base64
import colorsys
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DenseCell:
    left: int
    top: int
    width: int
    height: int
    dx: float
    dy: float
    magnitude: float
    hue_degrees: float
    fill: str


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def load_vectors_document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def vector_displacement(vector: dict[str, Any]) -> tuple[float, float]:
    return (
        float(vector["dst_x"]) - float(vector["src_x"]),
        float(vector["dst_y"]) - float(vector["src_y"]),
    )


def vector_magnitude(vector: dict[str, Any]) -> float:
    dx, dy = vector_displacement(vector)
    return math.hypot(dx, dy)


def select_representative_frame(frames: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [frame for frame in frames if frame.get("vector_count", 0) > 0]
    if not candidates:
        raise ValueError("no frames with vectors are available")
    return max(
        candidates,
        key=lambda frame: (
            frame.get("vector_count", 0) * frame.get("average_magnitude", 0.0),
            frame.get("vector_count", 0),
            frame.get("average_magnitude", 0.0),
            -frame.get("frame_index", 0),
        ),
    )


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * clamp(ratio, 0.0, 1.0))
    return ordered[index]


def motion_to_fill(dx: float, dy: float, magnitude: float, magnitude_reference: float) -> tuple[str, float]:
    hue_degrees = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
    normalized = clamp(magnitude / max(magnitude_reference, 1e-6), 0.0, 1.0)
    saturation = 0.18 + normalized * 0.82
    value = 0.16 + normalized * 0.84
    red, green, blue = colorsys.hsv_to_rgb(hue_degrees / 360.0, saturation, value)
    fill = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
    return fill, hue_degrees


def aggregate_dense_cells(
    vectors: list[dict[str, Any]],
    *,
    magnitude_reference: float | None = None,
) -> tuple[list[DenseCell], dict[str, Any]]:
    if not vectors:
        return [], {"magnitude_reference": 1.0, "max_magnitude": 0.0, "cell_count": 0}

    grouped: dict[tuple[int, int, int, int], dict[str, float]] = {}
    magnitudes: list[float] = []
    for vector in vectors:
        width = int(vector["w"])
        height = int(vector["h"])
        left = int(round(float(vector["dst_x"]) - width / 2))
        top = int(round(float(vector["dst_y"]) - height / 2))
        dx, dy = vector_displacement(vector)
        magnitude = math.hypot(dx, dy)
        magnitudes.append(magnitude)
        key = (left, top, width, height)
        bucket = grouped.setdefault(
            key,
            {"dx_sum": 0.0, "dy_sum": 0.0, "magnitude_sum": 0.0, "count": 0.0},
        )
        bucket["dx_sum"] += dx
        bucket["dy_sum"] += dy
        bucket["magnitude_sum"] += magnitude
        bucket["count"] += 1.0

    reference = magnitude_reference or percentile(magnitudes, 0.95)
    cells: list[DenseCell] = []
    for (left, top, width, height), bucket in sorted(grouped.items()):
        count = max(bucket["count"], 1.0)
        dx = bucket["dx_sum"] / count
        dy = bucket["dy_sum"] / count
        magnitude = math.hypot(dx, dy)
        fill, hue_degrees = motion_to_fill(dx, dy, magnitude, reference)
        cells.append(
            DenseCell(
                left=left,
                top=top,
                width=width,
                height=height,
                dx=dx,
                dy=dy,
                magnitude=magnitude,
                hue_degrees=hue_degrees,
                fill=fill,
            )
        )

    bounds = {
        "magnitude_reference": round(reference, 6),
        "max_magnitude": round(max(magnitudes), 6),
        "cell_count": len(cells),
        "min_left": min(cell.left for cell in cells),
        "min_top": min(cell.top for cell in cells),
        "max_right": max(cell.left + cell.width for cell in cells),
        "max_bottom": max(cell.top + cell.height for cell in cells),
    }
    return cells, bounds


def encode_png_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_direction_wheel_svg(cx: int, cy: int, radius: int) -> str:
    segments: list[str] = []
    for degree in range(0, 360, 10):
        next_degree = degree + 10
        theta_a = math.radians(degree)
        theta_b = math.radians(next_degree)
        x1 = cx + radius * math.cos(theta_a)
        y1 = cy + radius * math.sin(theta_a)
        x2 = cx + radius * math.cos(theta_b)
        y2 = cy + radius * math.sin(theta_b)
        large_arc = 0
        fill, _ = motion_to_fill(math.cos(theta_a), math.sin(theta_a), 1.0, 1.0)
        segments.append(
            (
                f"<path d='M {cx} {cy} L {x1:.2f} {y1:.2f} "
                f"A {radius} {radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z' "
                f"fill='{fill}' opacity='0.95' />"
            )
        )
    labels = [
        ("right", cx + radius + 24, cy + 4),
        ("down", cx - 18, cy + radius + 24),
        ("left", cx - radius - 44, cy + 4),
        ("up", cx - 10, cy - radius - 14),
    ]
    label_nodes = [
        f"<text x='{x}' y='{y}' font-family='IBM Plex Sans, sans-serif' font-size='15' fill='#f8fafc'>{label}</text>"
        for label, x, y in labels
    ]
    return "\n".join(
        [
            *segments,
            f"<circle cx='{cx}' cy='{cy}' r='{radius * 0.34}' fill='#081018' opacity='0.92' />",
            *label_nodes,
        ]
    )


def build_magnitude_scale_svg(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    magnitude_reference: float,
) -> str:
    steps = 48
    rects: list[str] = []
    for index in range(steps):
        ratio = index / max(steps - 1, 1)
        fill, _ = motion_to_fill(1.0, 0.0, ratio * magnitude_reference, magnitude_reference)
        rects.append(
            f"<rect x='{x + (width * ratio):.2f}' y='{y}' width='{width / steps + 1:.2f}' height='{height}' fill='{fill}' />"
        )
    return "\n".join(
        [
            *rects,
            f"<rect x='{x}' y='{y}' width='{width}' height='{height}' fill='none' stroke='rgba(255,255,255,0.35)' />",
            f"<text x='{x}' y='{y - 10}' font-family='IBM Plex Sans, sans-serif' font-size='15' fill='#f8fafc'>Magnitude scale</text>",
            f"<text x='{x}' y='{y + height + 18}' font-family='IBM Plex Sans, sans-serif' font-size='13' fill='#d6dee6'>0 px/frame</text>",
            f"<text x='{x + width - 96}' y='{y + height + 18}' font-family='IBM Plex Sans, sans-serif' font-size='13' fill='#d6dee6'>{magnitude_reference:.2f} px/frame</text>",
        ]
    )


def build_svg_document(
    *,
    frame_width: int,
    frame_height: int,
    title: str,
    subtitle: str,
    cells: list[DenseCell],
    magnitude_reference: float,
    frame_data_uri: str | None = None,
    overlay_alpha: float = 0.65,
) -> str:
    panel_height = 136
    total_height = frame_height + panel_height
    rects = []
    for cell in cells:
        rects.append(
            (
                f"<rect x='{cell.left}' y='{cell.top}' width='{cell.width}' height='{cell.height}' "
                f"fill='{cell.fill}' shape-rendering='crispEdges' />"
            )
        )

    frame_layer = ""
    if frame_data_uri is not None:
        frame_layer = (
            f"<image href='{frame_data_uri}' x='0' y='0' width='{frame_width}' height='{frame_height}' preserveAspectRatio='none' />"
            f"<rect x='0' y='0' width='{frame_width}' height='{frame_height}' fill='#071018' opacity='{clamp(overlay_alpha, 0.0, 1.0):.3f}' />"
        )

    legend_x = max(frame_width - 220, 18)
    magnitude_scale = build_magnitude_scale_svg(
        x=24,
        y=frame_height + 70,
        width=min(340, max(frame_width - 280, 220)),
        height=18,
        magnitude_reference=magnitude_reference,
    )
    direction_wheel = build_direction_wheel_svg(legend_x, frame_height + 68, 42)

    return "\n".join(
        [
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{frame_width}' height='{total_height}' viewBox='0 0 {frame_width} {total_height}'>",
            "<rect width='100%' height='100%' fill='#04070a' />",
            frame_layer,
            *rects,
            f"<rect x='0' y='0' width='{frame_width}' height='{frame_height}' fill='none' stroke='rgba(255,255,255,0.15)' />",
            f"<text x='24' y='{frame_height + 30}' font-family='IBM Plex Sans, sans-serif' font-size='24' fill='#f8fafc'>{title}</text>",
            f"<text x='24' y='{frame_height + 52}' font-family='IBM Plex Sans, sans-serif' font-size='14' fill='#d6dee6'>{subtitle}</text>",
            magnitude_scale,
            direction_wheel,
            "</svg>",
            "",
        ]
    )


def extract_frame_png(ffmpeg_bin: str, video_path: Path, timestamp: float, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.6f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def rasterize_svg(ffmpeg_bin: str, svg_path: Path, png_path: Path) -> None:
    command = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(svg_path),
        str(png_path),
    ]
    subprocess.run(command, check=True)


def render_dense_flow(
    *,
    vectors_path: Path,
    video_path: Path,
    output_dir: Path,
    ffmpeg_bin: str,
    frame_index: int | None = None,
    overlay_alpha: float = 0.65,
) -> dict[str, Any]:
    document = load_vectors_document(vectors_path)
    chosen_frame = (
        document["frames"][frame_index]
        if frame_index is not None
        else select_representative_frame(document["frames"])
    )
    cells, bounds = aggregate_dense_cells(chosen_frame["vectors"])
    frame_width = int(bounds["max_right"] - min(0, bounds["min_left"]))
    frame_height = int(bounds["max_bottom"] - min(0, bounds["min_top"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    frame_png_path = output_dir / "frame.png"
    raw_svg_path = output_dir / "dense-flow-raw.svg"
    raw_png_path = output_dir / "dense-flow-raw.png"
    overlay_svg_path = output_dir / "dense-flow-overlay.svg"
    overlay_png_path = output_dir / "dense-flow-overlay.png"
    summary_path = output_dir / "summary.json"

    extract_frame_png(ffmpeg_bin, video_path, float(chosen_frame["timestamp"]), frame_png_path)

    raw_svg_path.write_text(
        build_svg_document(
            frame_width=frame_width,
            frame_height=frame_height,
            title="Dense codec motion field",
            subtitle=(
                f"frame {chosen_frame['frame_index']} at {float(chosen_frame['timestamp']):.3f}s "
                f"• hue = direction • brightness/saturation = magnitude"
            ),
            cells=cells,
            magnitude_reference=bounds["magnitude_reference"],
        ),
        encoding="utf-8",
    )

    overlay_svg_path.write_text(
        build_svg_document(
            frame_width=frame_width,
            frame_height=frame_height,
            title="Dense codec motion field overlay",
            subtitle=(
                f"frame {chosen_frame['frame_index']} at {float(chosen_frame['timestamp']):.3f}s "
                f"• codec grid stays block-sized ({sorted({cell.width for cell in cells})} px blocks)"
            ),
            cells=cells,
            magnitude_reference=bounds["magnitude_reference"],
            frame_data_uri=encode_png_data_uri(frame_png_path),
            overlay_alpha=overlay_alpha,
        ),
        encoding="utf-8",
    )

    rasterize_svg(ffmpeg_bin, raw_svg_path, raw_png_path)
    rasterize_svg(ffmpeg_bin, overlay_svg_path, overlay_png_path)

    summary = {
        "vectors_path": str(vectors_path),
        "video_path": str(video_path),
        "frame_index": chosen_frame["frame_index"],
        "timestamp_seconds": float(chosen_frame["timestamp"]),
        "vector_count": chosen_frame["vector_count"],
        "average_magnitude": chosen_frame["average_magnitude"],
        "magnitude_reference": bounds["magnitude_reference"],
        "max_magnitude": bounds["max_magnitude"],
        "dense_cell_count": bounds["cell_count"],
        "block_widths": sorted({cell.width for cell in cells}),
        "block_heights": sorted({cell.height for cell in cells}),
        "overlay_alpha": overlay_alpha,
        "artifacts": {
            "frame_png": str(frame_png_path),
            "raw_svg": str(raw_svg_path),
            "raw_png": str(raw_png_path),
            "overlay_svg": str(overlay_svg_path),
            "overlay_png": str(overlay_png_path),
        },
        "limitations": [
            "The visualization is dense only across the codec motion-vector grid, not per pixel.",
            "Block sizes and coverage depend on the encoded stream and decoder-exposed motion vectors.",
            "Colors encode direction by hue and motion magnitude by saturation/value.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--frame-index", type=int)
    parser.add_argument("--overlay-alpha", type=float, default=0.65)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = render_dense_flow(
        vectors_path=args.vectors,
        video_path=args.video,
        output_dir=args.output_dir,
        ffmpeg_bin=args.ffmpeg_bin,
        frame_index=args.frame_index,
        overlay_alpha=args.overlay_alpha,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import render_dense_flow


class RenderDenseFlowTests(unittest.TestCase):
    def test_select_representative_frame_prefers_total_motion(self) -> None:
        frames = [
            {"frame_index": 0, "vector_count": 800, "average_magnitude": 0.2},
            {"frame_index": 1, "vector_count": 200, "average_magnitude": 3.0},
            {"frame_index": 2, "vector_count": 1000, "average_magnitude": 0.1},
        ]

        chosen = render_dense_flow.select_representative_frame(frames)

        self.assertEqual(chosen["frame_index"], 1)

    def test_aggregate_dense_cells_keeps_codec_grid_and_color_metadata(self) -> None:
        cells, bounds = render_dense_flow.aggregate_dense_cells(
            [
                {
                    "w": 16,
                    "h": 16,
                    "src_x": 4,
                    "src_y": 8,
                    "dst_x": 8,
                    "dst_y": 8,
                },
                {
                    "w": 16,
                    "h": 16,
                    "src_x": 0,
                    "src_y": 8,
                    "dst_x": 8,
                    "dst_y": 8,
                },
                {
                    "w": 8,
                    "h": 8,
                    "src_x": 20,
                    "src_y": 20,
                    "dst_x": 24,
                    "dst_y": 20,
                },
            ]
        )

        self.assertEqual(bounds["cell_count"], 2)
        self.assertEqual(cells[0].left, 0)
        self.assertEqual(cells[0].top, 0)
        self.assertEqual(cells[0].width, 16)
        self.assertAlmostEqual(cells[0].dx, 6.0)
        self.assertTrue(cells[0].fill.startswith("#"))
        self.assertGreaterEqual(bounds["magnitude_reference"], 4.0)

    def test_render_dense_flow_writes_summary_and_artifact_paths(self) -> None:
        document = {
            "frames": [
                {
                    "frame_index": 0,
                    "timestamp": 0.5,
                    "vector_count": 2,
                    "average_magnitude": 2.5,
                    "vectors": [
                        {
                            "w": 16,
                            "h": 16,
                            "src_x": 4,
                            "src_y": 8,
                            "dst_x": 8,
                            "dst_y": 8,
                        },
                        {
                            "w": 8,
                            "h": 8,
                            "src_x": 18,
                            "src_y": 20,
                            "dst_x": 24,
                            "dst_y": 20,
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            vectors_path = tmp_path / "vectors.json"
            vectors_path.write_text(__import__("json").dumps(document))
            video_path = tmp_path / "clip.mp4"
            video_path.write_bytes(b"video")
            output_dir = tmp_path / "dense-flow"

            def fake_extract(_ffmpeg_bin: str, _video_path: Path, _timestamp: float, output_path: Path) -> None:
                output_path.write_bytes(b"png")

            def fake_rasterize(_ffmpeg_bin: str, svg_path: Path, png_path: Path) -> None:
                png_path.write_bytes(svg_path.read_bytes())

            with mock.patch("scripts.render_dense_flow.extract_frame_png", side_effect=fake_extract):
                with mock.patch("scripts.render_dense_flow.rasterize_svg", side_effect=fake_rasterize):
                    summary = render_dense_flow.render_dense_flow(
                        vectors_path=vectors_path,
                        video_path=video_path,
                        output_dir=output_dir,
                        ffmpeg_bin="ffmpeg",
                    )

            self.assertEqual(summary["frame_index"], 0)
            self.assertEqual(summary["dense_cell_count"], 2)
            self.assertEqual(summary["block_widths"], [8, 16])
            self.assertTrue((output_dir / "dense-flow-raw.svg").is_file())
            self.assertTrue((output_dir / "dense-flow-overlay.svg").is_file())
            self.assertTrue((output_dir / "summary.json").is_file())


if __name__ == "__main__":
    unittest.main()

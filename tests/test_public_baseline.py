import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import public_baseline


class PublicBaselineTests(unittest.TestCase):
    def test_load_manifest_requires_two_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "run_id": "bad",
                        "inputs": [{"name": "only-one"}],
                        "artifacts": {"report_dir": "reports/out/example"},
                    }
                )
            )

            with self.assertRaisesRegex(ValueError, "exactly two inputs"):
                public_baseline.load_manifest(manifest_path)

    def test_summarize_ffprobe_frames(self) -> None:
        ffprobe_doc = {
            "frames": [
                {"pict_type": "I", "best_effort_timestamp_time": "0.000000"},
                {
                    "pict_type": "P",
                    "best_effort_timestamp_time": "0.083333",
                    "side_data_list": [
                        {
                            "side_data_type": "Motion vectors",
                            "motion_vectors": [
                                {"src_x": 10, "src_y": 10, "dst_x": 13, "dst_y": 14},
                                {"src_x": 5, "src_y": 6, "dst_x": 5, "dst_y": 9},
                            ],
                        }
                    ],
                },
            ]
        }

        summary = public_baseline.summarize_ffprobe_frames(ffprobe_doc)

        self.assertEqual(summary["frame_count"], 2)
        self.assertEqual(summary["frames_with_vectors"], 1)
        self.assertEqual(summary["total_vectors"], 2)
        self.assertAlmostEqual(summary["mean_vector_magnitude"], 4.0)
        self.assertEqual(summary["frames"][0]["vector_count"], 0)
        self.assertEqual(summary["frames"][1]["vector_count"], 2)

    def test_build_comparison_summary_and_svg(self) -> None:
        per_input = {
            "input-a": {
                "frame_count": 4,
                "frames_with_vectors": 3,
                "total_vectors": 40,
                "mean_vector_magnitude": 2.5,
            },
            "input-b": {
                "frame_count": 4,
                "frames_with_vectors": 2,
                "total_vectors": 10,
                "mean_vector_magnitude": 1.25,
            },
        }

        comparison = public_baseline.build_comparison_summary(per_input)
        svg = public_baseline.build_comparison_svg(comparison)

        self.assertEqual(comparison["higher_vector_count_input"], "input-a")
        self.assertEqual(comparison["delta"]["vector_count"], 30)
        self.assertIn("input-a", svg)
        self.assertIn("vectors: 40", svg)

    def test_run_baseline_writes_blocked_report_without_ffmpeg(self) -> None:
        manifest = {
            "run_id": "public-known-good-baseline",
            "inputs": [
                {
                    "name": "input-a",
                    "relative_output_path": "datasets/fixtures/input-a.mp4",
                    "generator": {
                        "video_filter": "testsrc=duration=1:size=16x16:rate=1",
                        "frame_rate": 1,
                        "codec": "libx264",
                        "pixel_format": "yuv420p",
                        "gop_size": 1,
                        "bf": 0,
                    },
                },
                {
                    "name": "input-b",
                    "relative_output_path": "datasets/fixtures/input-b.mp4",
                    "generator": {
                        "video_filter": "testsrc=duration=1:size=16x16:rate=1",
                        "frame_rate": 1,
                        "codec": "libx264",
                        "pixel_format": "yuv420p",
                        "gop_size": 1,
                        "bf": 0,
                    },
                },
            ],
            "artifacts": {
                "report_dir": "reports/out/public-known-good-baseline",
                "vectors_dir": "reports/out/public-known-good-baseline/vectors",
                "renders_dir": "reports/out/public-known-good-baseline/renders",
                "comparison_dir": "reports/out/public-known-good-baseline/comparison",
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / "datasets" / "fixtures").mkdir(parents=True)
            with mock.patch.object(public_baseline, "REPO_ROOT", repo_root):
                with mock.patch("scripts.public_baseline.shutil.which", return_value=None):
                    exit_code = public_baseline.run_baseline(manifest)

            self.assertEqual(exit_code, 2)
            status_path = repo_root / "reports" / "out" / "public-known-good-baseline" / "status.json"
            report_path = repo_root / "reports" / "out" / "public-known-good-baseline" / "report.md"
            self.assertTrue(status_path.exists())
            self.assertTrue(report_path.exists())
            status = json.loads(status_path.read_text())
            self.assertEqual(status["status"], "blocked")
            self.assertIn("ffmpeg", status["missing_tools"])


if __name__ == "__main__":
    unittest.main()

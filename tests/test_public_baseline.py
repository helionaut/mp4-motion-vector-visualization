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
                        "paths": {"vectors_dir": "reports/out/example/vectors"},
                        "tooling": {"ffprobe_bin": "/tmp/ffprobe"},
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
        self.assertEqual(summary["frames_with_motion_side_data"], 1)
        self.assertEqual(summary["total_vectors"], 2)
        self.assertAlmostEqual(summary["mean_vector_magnitude"], 4.0)
        self.assertEqual(summary["frames"][0]["vector_count"], 0)
        self.assertEqual(summary["frames"][1]["vector_count"], 2)

    def test_build_comparison_summary_and_svg(self) -> None:
        per_input = {
            "input-a": {
                "frame_count": 4,
                "frames_with_vectors": 3,
                "frames_with_motion_side_data": 3,
                "total_vectors": 40,
                "mean_vector_magnitude": 2.5,
            },
            "input-b": {
                "frame_count": 4,
                "frames_with_vectors": 2,
                "frames_with_motion_side_data": 2,
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

    def test_run_baseline_writes_blocked_report_when_bootstrap_fails(self) -> None:
        manifest = {
            "run_id": "public-baseline",
            "inputs": [
                {
                    "name": "input-a",
                    "raw_path": "/tmp/input-a.mp4",
                    "source_url": "https://example.com/a.mp4",
                },
                {
                    "name": "input-b",
                    "raw_path": "/tmp/input-b.mp4",
                    "source_url": "https://example.com/b.mp4",
                },
            ],
            "paths": {
                "manifest_path": "manifests/public-baseline.json",
                "vectors_dir": "reports/out/public-baseline/vectors",
                "renders_dir": "reports/out/public-baseline/renders",
                "comparison_dir": "reports/out/public-baseline/comparison",
            },
            "tooling": {"ffprobe_bin": "/tmp/ffprobe"},
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            with mock.patch.object(public_baseline, "REPO_ROOT", repo_root):
                with mock.patch("scripts.public_baseline.run_command", side_effect=FileNotFoundError("missing ffmpeg")):
                    exit_code = public_baseline.run_baseline(manifest)

            self.assertEqual(exit_code, 2)
            status_path = repo_root / "reports" / "out" / "public-baseline" / "status.json"
            report_path = repo_root / "reports" / "out" / "public-baseline" / "report.md"
            self.assertTrue(status_path.exists())
            status = json.loads(status_path.read_text())
            self.assertEqual(status["status"], "blocked")
            self.assertEqual(status["blocked_by"], "ffmpeg-bootstrap-failed")
            self.assertTrue(report_path.exists())

    def test_print_plan_uses_prepared_manifest_inputs(self) -> None:
        manifest = {
            "run_id": "public-baseline",
            "inputs": [
                {"name": "a", "raw_path": "/tmp/a.mp4", "source_url": "https://example.com/a.mp4"},
                {"name": "b", "raw_path": "/tmp/b.mp4", "source_url": "https://example.com/b.mp4"},
            ],
            "paths": {
                "vectors_dir": "reports/out/public-baseline/vectors",
                "renders_dir": "reports/out/public-baseline/renders",
                "comparison_dir": "reports/out/public-baseline/comparison",
            },
            "tooling": {"ffprobe_bin": "/tmp/ffprobe"},
        }

        with mock.patch("sys.stdout.write") as mock_write:
            public_baseline.print_plan(manifest)

        written = "".join(call.args[0] for call in mock_write.call_args_list)
        self.assertIn("scripts/prepare_public_inputs.sh", written)
        self.assertIn("/tmp/a.mp4", written)


if __name__ == "__main__":
    unittest.main()

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
                "total_motion_vector_payload_bytes": 400,
                "mean_motion_vector_payload_bytes": 133.333333,
            },
            "input-b": {
                "frame_count": 4,
                "frames_with_vectors": 2,
                "frames_with_motion_side_data": 2,
                "total_vectors": 10,
                "mean_vector_magnitude": 1.25,
                "total_motion_vector_payload_bytes": 100,
                "mean_motion_vector_payload_bytes": 50.0,
            },
        }

        comparison = public_baseline.build_comparison_summary(per_input)
        svg = public_baseline.build_comparison_svg(comparison)

        self.assertEqual(comparison["higher_motion_vector_payload_input"], "input-a")
        self.assertEqual(comparison["delta"]["vector_count"], 30)
        self.assertEqual(comparison["delta"]["motion_vector_payload_bytes"], 300)
        self.assertIn("input-a", svg)
        self.assertIn("vectors: 40", svg)

    def test_build_libavcodec_extract_command(self) -> None:
        command = public_baseline.build_libavcodec_extract_command(
            Path("/tmp/extractor"),
            {"name": "input-a", "raw_path": "/tmp/input-a.mp4"},
            Path("/tmp/output.json"),
        )

        self.assertEqual(
            command,
            [
                "/tmp/extractor",
                "--input",
                "/tmp/input-a.mp4",
                "--input-name",
                "input-a",
                "--output",
                "/tmp/output.json",
                "--summary-output",
                "/tmp/output.summary.json",
            ],
        )

    def test_build_dense_flow_command(self) -> None:
        command = public_baseline.build_dense_flow_command(
            Path("/tmp/ffmpeg"),
            {"name": "input-a", "raw_path": "/tmp/input-a.mp4"},
            Path("/tmp/vectors.json"),
            Path("/tmp/dense-flow/input-a"),
        )

        self.assertEqual(
            command,
            [
                "python3",
                "scripts/render_dense_flow.py",
                "--vectors",
                "/tmp/vectors.json",
                "--video",
                "/tmp/input-a.mp4",
                "--output-dir",
                "/tmp/dense-flow/input-a",
                "--ffmpeg-bin",
                "/tmp/ffmpeg",
                "--overlay-alpha",
                "0.58",
            ],
        )

    def test_extract_summary_sidecar_path(self) -> None:
        summary_path = public_baseline.extract_summary_sidecar_path(Path("/tmp/output.json"))

        self.assertEqual(summary_path, Path("/tmp/output.summary.json"))

    def test_load_extract_summary_prefers_compact_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "vectors.json"
            output_path.write_text("{not valid json")
            sidecar_path = public_baseline.extract_summary_sidecar_path(output_path)
            sidecar_path.write_text(
                json.dumps(
                    {
                        "frame_count": 12,
                        "frames_with_vectors": 10,
                        "frames_with_motion_side_data": 10,
                        "total_vectors": 345,
                        "mean_vector_magnitude": 1.25,
                        "coordinate_vectors_available": True,
                    }
                )
            )

            summary = public_baseline.load_extract_summary(output_path)

        self.assertEqual(summary["total_vectors"], 345)
        self.assertTrue(summary["coordinate_vectors_available"])

    def test_load_extract_summary_falls_back_to_full_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "vectors.json"
            output_path.write_text(
                json.dumps(
                    {
                        "frame_count": 4,
                        "frames_with_vectors": 2,
                        "frames_with_motion_side_data": 3,
                        "total_vectors": 6,
                        "mean_vector_magnitude": 2.0,
                        "coordinate_vectors_available": True,
                        "frames": [],
                    }
                )
            )

            summary = public_baseline.load_extract_summary(output_path)

        self.assertEqual(summary["frame_count"], 4)
        self.assertEqual(summary["total_vectors"], 6)

    def test_summarize_ffmpeg_showinfo_tracks_payload_bytes(self) -> None:
        log_text = """
[Parsed_showinfo_0 @ 0x1] n:   0 pts:      0 pts_time:0 duration:    512 duration_time:0.0416667 fmt:yuv420p cl:left sar:1/1 s:854x480 i:P iskey:1 type:I checksum:ABC
[Parsed_showinfo_0 @ 0x1] n:   1 pts:    512 pts_time:0.0416667 duration:    512 duration_time:0.0416667 fmt:yuv420p cl:left sar:1/1 s:854x480 i:P iskey:0 type:P checksum:DEF
[Parsed_showinfo_0 @ 0x1]   side data - Motion vectors: (129600 bytes)
[Parsed_showinfo_0 @ 0x1] n:   2 pts:   1024 pts_time:0.0833333 duration:    512 duration_time:0.0416667 fmt:yuv420p cl:left sar:1/1 s:854x480 i:P iskey:0 type:B checksum:GHI
[Parsed_showinfo_0 @ 0x1]   side data - Motion vectors: (110680 bytes)
""".strip()

        summary = public_baseline.summarize_ffmpeg_showinfo(log_text)

        self.assertEqual(summary["frame_count"], 3)
        self.assertEqual(summary["frames_with_motion_side_data"], 2)
        self.assertEqual(summary["total_motion_vector_payload_bytes"], 240280)
        self.assertEqual(summary["max_motion_vector_payload_bytes"], 129600)
        self.assertFalse(summary["coordinate_vectors_available"])
        self.assertEqual(summary["frames"][1]["motion_vector_payload_bytes"], 129600)

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
                    exit_code = public_baseline.run_baseline(
                        manifest,
                        progress_artifact=repo_root / ".symphony" / "progress" / "HEL-155.json",
                    )

            self.assertEqual(exit_code, 2)
            status_path = repo_root / "reports" / "out" / "public-baseline" / "status.json"
            report_path = repo_root / "reports" / "out" / "public-baseline" / "report.md"
            self.assertTrue(status_path.exists())
            status = json.loads(status_path.read_text())
            self.assertEqual(status["status"], "blocked")
            self.assertEqual(status["blocked_by"], "ffmpeg-bootstrap-failed")
            self.assertEqual(
                status["expected_command_surface"],
                "python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json",
            )
            self.assertTrue(report_path.exists())

    def test_build_report_title_uses_run_id(self) -> None:
        self.assertEqual(
            public_baseline.build_report_title({"run_id": "user-validation"}),
            "User Validation Report",
        )

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
        self.assertIn("scripts/bootstrap_host_libavcodec.sh --output build/host/libavcodec_mv_extractor", written)
        self.assertIn("/tmp/a.mp4", written)


if __name__ == "__main__":
    unittest.main()

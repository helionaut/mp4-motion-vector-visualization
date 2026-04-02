from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_inputs import Layout, build_layout, make_manifest, summarize_probe


class PrepareInputsTests(unittest.TestCase):
    def test_build_layout_uses_public_and_private_roots(self) -> None:
        root = Path("/tmp/datasets-root")
        layout = build_layout(root, "run-123")

        self.assertEqual(layout.public_raw_dir, root / "public" / "raw" / "run-123")
        self.assertEqual(layout.public_prepared_dir, root / "public" / "prepared" / "run-123")
        self.assertEqual(layout.private_raw_dir, root / "user" / "raw" / "run-123")
        self.assertEqual(layout.private_prepared_dir, root / "user" / "prepared" / "run-123")

    def test_summarize_probe_extracts_expected_fields(self) -> None:
        probe = {
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "30.0", "bit_rate": "1000", "size": "42"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "profile": "High",
                    "width": 640,
                    "height": 360,
                    "pix_fmt": "yuv420p",
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"},
            ],
        }

        summary = summarize_probe(probe)

        self.assertEqual(summary["video_codec"], "h264")
        self.assertEqual(summary["audio_codec"], "aac")
        self.assertEqual(summary["width"], 640)
        self.assertEqual(summary["audio_channels"], 2)

    def test_make_manifest_writes_probe_sidecars_and_private_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            datasets_root = tmp_path / "datasets"
            raw_dir = datasets_root / "public" / "raw" / "public-baseline"
            raw_dir.mkdir(parents=True)

            raw_file = raw_dir / "clip.mp4"
            raw_file.write_bytes(b"synthetic-mp4")

            config = {
                "manifest_version": 1,
                "run_id": "public-baseline",
                "comparison_label": "test",
                "visibility": "public",
                "source_page_url": "https://example.com/source",
                "license_url": "https://example.com/license",
                "license_notes": "notes",
                "notes": ["note"],
                "inputs": [
                    {
                        "name": "clip",
                        "visibility": "public",
                        "filename": "clip.mp4",
                        "source_url": "https://example.com/clip.mp4",
                        "provenance": "example/source",
                        "notes": "sample",
                    }
                ],
            }
            layout = Layout(
                datasets_root=datasets_root,
                public_raw_dir=raw_dir,
                public_prepared_dir=datasets_root / "public" / "prepared" / "public-baseline",
                private_raw_dir=datasets_root / "user" / "raw" / "public-baseline",
                private_prepared_dir=datasets_root / "user" / "prepared" / "public-baseline",
            )
            manifest_path = tmp_path / "manifests" / "public-baseline.json"

            def fake_probe(_ffprobe_bin: str, _input_path: Path) -> dict[str, object]:
                return {
                    "format": {"format_name": "mp4", "duration": "1.0", "bit_rate": "8", "size": "13"},
                    "streams": [{"codec_type": "video", "codec_name": "h264", "width": 16, "height": 9}],
                }

            import scripts.prepare_inputs as prepare_inputs

            original_probe = prepare_inputs.probe_file
            original_ensure = prepare_inputs.ensure_file
            try:
                prepare_inputs.probe_file = fake_probe
                prepare_inputs.ensure_file = lambda _url, _destination: None
                manifest = make_manifest(
                    config=config,
                    layout=layout,
                    ffprobe_bin="/tmp/ffprobe",
                    manifest_path=manifest_path,
                )
            finally:
                prepare_inputs.probe_file = original_probe
                prepare_inputs.ensure_file = original_ensure

            probe_path = layout.public_prepared_dir / "probe" / "clip.ffprobe.json"
            self.assertTrue(probe_path.is_file())
            self.assertEqual(manifest["inputs"][0]["raw_path"], str(raw_file))
            self.assertEqual(manifest["private_input_contract"]["expected_raw_dir"], str(layout.private_raw_dir))
            self.assertEqual(json.loads(probe_path.read_text(encoding="utf-8"))["format"]["format_name"], "mp4")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_private_input_config import find_missing_private_inputs


class ValidatePrivateInputConfigTests(unittest.TestCase):
    def test_flags_placeholder_private_paths(self) -> None:
        config = {
            "visibility": "private",
            "inputs": [
                {
                    "name": "before",
                    "visibility": "private",
                    "local_path": "replace/with/first.mp4",
                },
                {
                    "name": "after",
                    "visibility": "private",
                    "local_path": "/path/to/second.mp4",
                },
            ],
        }

        missing = find_missing_private_inputs(config)

        self.assertEqual(
            missing,
            [
                {
                    "name": "before",
                    "reason": "placeholder-local-path",
                    "local_path": "replace/with/first.mp4",
                },
                {
                    "name": "after",
                    "reason": "placeholder-local-path",
                    "local_path": "/path/to/second.mp4",
                },
            ],
        )

    def test_allows_real_private_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = tmp_path / "first.mp4"
            second = tmp_path / "second.mp4"
            first.write_bytes(b"first")
            second.write_bytes(b"second")

            config = {
                "visibility": "private",
                "inputs": [
                    {"name": "before", "visibility": "private", "local_path": str(first)},
                    {"name": "after", "visibility": "private", "local_path": str(second)},
                ],
            }

            self.assertEqual(find_missing_private_inputs(config), [])

    def test_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = {
                "visibility": "private",
                "inputs": [
                    {
                        "name": "before",
                        "visibility": "private",
                        "local_path": str(tmp_path / "missing.mp4"),
                    }
                ],
            }

            self.assertEqual(
                find_missing_private_inputs(config),
                [
                    {
                        "name": "before",
                        "reason": "local-path-not-found",
                        "local_path": str(tmp_path / "missing.mp4"),
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()

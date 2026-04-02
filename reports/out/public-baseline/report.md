# Public Baseline Report

- Run id: `public-baseline`
- Status: blocked
- Blocked by: `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors`
- Host command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`
- Docker command surface: `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`
- Notes:
  - ffmpeg decode-path extraction completed for both public MP4 inputs
  - codecview render artifacts were written
  - motion-vector side-data bytes are present on the FFmpeg decode path, but the CLI still does not serialize coordinate-bearing vectors
- Details:
  - `bbb_480p_30s`: `{"frame_count": 720, "frames_with_motion_side_data": 714, "frames_with_vectors": 0, "total_motion_vector_payload_bytes": 66011680, "total_vectors": 0}`
  - `bbb_1080p_30s`: `{"frame_count": 720, "frames_with_motion_side_data": 714, "frames_with_vectors": 0, "total_motion_vector_payload_bytes": 337375720, "total_vectors": 0}`


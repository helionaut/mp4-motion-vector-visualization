# Public Baseline Report

- Run id: `public-baseline`
- Status: blocked
- Blocked by: `motion-vector-payload-missing`
- Command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`
- Notes:
  - ffprobe completed for both public MP4 inputs
  - codecview render artifacts were written
  - motion-vector side-data markers are present, but the ffprobe JSON payload does not include coordinate arrays
- Details:
  - `bbb_480p_30s`: `{"frame_count": 720, "frames_with_motion_side_data": 714, "frames_with_vectors": 0, "total_vectors": 0}`
  - `bbb_1080p_30s`: `{"frame_count": 720, "frames_with_motion_side_data": 714, "frames_with_vectors": 0, "total_vectors": 0}`


# Public Known-Good Baseline Report

- Run id: `public-known-good-baseline`
- Status: blocked on missing runtime binaries in the current host workspace
- Missing tools: `ffmpeg, ffprobe`
- Reproduction command once Docker is available:
  `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json`

This failure is expected on hosts without Docker and FFmpeg. The runner and manifest are committed so a future agent can rerun the same baseline without mixing in private media.

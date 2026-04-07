# Public Baseline Report

- Run id: `public-baseline`
- Status: blocked
- Blocked by: `host-libavcodec-dev-surface-missing`
- Host bootstrap command: `scripts/bootstrap_host_libavcodec.sh --output build/host/libavcodec_mv_extractor`
- Host validation command: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-156.json`
- Notes:
  - the host-run libavcodec extractor could not be built on this machine
  - the prepared public baseline inputs and ffmpeg render surface remain unchanged
  - missing pkg-config entries for libavformat/libavcodec/libavutil
install the FFmpeg development packages for this host before rerunning the host extractor slice
- Details:
  - `bootstrap_command`: `["scripts/bootstrap_host_libavcodec.sh", "--output", "build/host/libavcodec_mv_extractor"]`
  - `ffmpeg_bin`: `"/home/helionaut/srv/research-cache/18afd661ce11/toolchains/ffmpeg-johnvansickle-static/ffmpeg"`
  - `ffprobe_bin`: `"/home/helionaut/srv/research-cache/18afd661ce11/toolchains/ffmpeg-johnvansickle-static/ffprobe"`


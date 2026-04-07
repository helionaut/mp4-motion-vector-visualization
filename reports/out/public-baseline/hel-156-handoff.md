# HEL-156 Handoff

- Original CEO request status: slice-shipped
- Delivered in this slice: added a repo-local host `libavcodec` motion-vector extractor, a host bootstrap/build script, and a host validation path that records the exact compile/runtime boundary on the prepared public baseline
- Still open from original request: coordinate-bearing motion vectors are still not serialized end-to-end, so the ingest/extract/compare workflow remains unproven on the prepared public pair
- Next recommended slice: rerun the committed HEL-156 host validation path on a machine where `pkg-config` resolves `libavformat`, `libavcodec`, and `libavutil`, then record whether the extractor emits non-empty coordinate vectors
- Environment blocker: host-libavcodec-dev-surface-missing
- Why this cannot be proven on the current machine: the current host has cached static `ffmpeg` / `ffprobe` binaries and `gcc`, but it does not expose the FFmpeg development packages needed to compile the new `libavcodec` extractor
- Infrastructure required to close the original ask: a machine with FFmpeg development headers/libraries available to `pkg-config`, and optionally a Docker-capable host for live container proof of the broader environment contract

## What changed

- Added `tools/host_libavcodec_mv_extractor.c`
- Added `scripts/bootstrap_host_libavcodec.sh`
- Switched `scripts/public_baseline.py` to the host `libavcodec` extraction surface for HEL-156 and updated the report/progress command surface
- Wrote fresh blocked-run evidence to:
  - `.symphony/progress/HEL-156.json`
  - `reports/out/public-baseline/status.json`
  - `reports/out/public-baseline/report.md`

## Observed result

- Validation command:
  - `python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-156.json`
- Exit code:
  - `4`
- Blocker recorded:
  - `host-libavcodec-dev-surface-missing`
- Exact bootstrap failure:
  - `missing pkg-config entries for libavformat/libavcodec/libavutil`

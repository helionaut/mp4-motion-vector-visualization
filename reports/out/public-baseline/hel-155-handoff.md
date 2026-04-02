# HEL-155 Handoff

- Original CEO request status: slice-shipped
- Delivered in this slice: switched the public baseline from the `ffprobe` JSON extractor to the FFmpeg decode path with `-export_side_data +mvs`, added a runtime progress artifact, refreshed codecview renders, and recorded the tighter failure boundary in machine-readable reports
- Still open from original request: coordinate-bearing motion-vector artifacts are still unavailable, so the original ingest/extract/compare ask is not yet fully proven
- Next recommended slice: replace only the coordinate-serialization surface with a libavcodec-backed extractor that can turn the now-proven side-data payload bytes into vector coordinates
- Environment blocker: docker CLI unavailable on the current machine for live container validation
- Why this cannot be proven on the current machine: the repo's Docker contract can be referenced and reused, but `scripts/run_in_docker.sh run -- ...` cannot execute here without `docker`
- Infrastructure required to close the original ask: one Docker-capable machine for live container proof, plus a coordinate-serialization extractor beyond the current FFmpeg CLI surface

## Shipped evidence

- Runtime progress artifact: `.symphony/progress/HEL-155.json`
- Status report: `reports/out/public-baseline/status.json`
- Human-readable report: `reports/out/public-baseline/report.md`
- Comparison evidence: `reports/out/public-baseline/comparison/summary.json` and `reports/out/public-baseline/comparison/summary.svg`
- Decode-path logs: `reports/out/public-baseline/vectors/*.ffmpeg-showinfo.log`

## Observed boundary

- Deterministic extractor command:
  - `/home/helionaut/srv/research-cache/18afd661ce11/toolchains/ffmpeg-johnvansickle-static/ffmpeg -hide_banner -export_side_data +mvs -i <input> -an -vf showinfo -f null -`
- `bbb_480p_30s`: 714/720 frames with motion-vector side data, `66,011,680` payload bytes, `0` coordinate vectors
- `bbb_1080p_30s`: 714/720 frames with motion-vector side data, `337,375,720` payload bytes, `0` coordinate vectors
- Blocker label written to `status.json`: `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors`

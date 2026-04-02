# Outcome Synthesis Report

Project: MP4 Motion Vector Visualization
Issue: HEL-153

## Verdict

The project has a reproducible public baseline, but it has not yet proven codec motion-vector extraction. The current blocker is not input preparation or report generation. It is the extractor surface itself.

## What is proven

- The repo has a stable research contract in `docs/PRD.md`, `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`.
- The public Big Buck Bunny input pair is reproducible through `scripts/prepare_public_inputs.sh` and `manifests/public-baseline.json`.
- `python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json` completes enough work to:
  - probe both MP4 inputs
  - render codecview artifacts for both inputs
  - emit a machine-readable status file and report under `reports/out/public-baseline/`
- The failure is reproducible and specific:
  - both inputs show `Motion vectors` side-data markers on 714 frames
  - both inputs still produce `frames_with_vectors=0`
  - both inputs still produce `total_vectors=0`

## What is blocked

- No committed command currently yields non-empty vector coordinates for the public baseline pair.
- Because vector JSON is empty, the comparison stage is not yet credible as a motion-vector comparison workflow.
- The private-data lane should stay parked until the public extractor lane produces real vectors; otherwise HEL-152 would only replay the same blocker on a new input pair.

## Reuse for the next issue

- Public manifest: `manifests/public-baseline.json`
- Public baseline runner: `scripts/public_baseline.py`
- Public input prep wrapper: `scripts/prepare_public_inputs.sh`
- Latest evidence:
  - `reports/out/public-baseline/status.json`
  - `reports/out/public-baseline/report.md`
- Shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`

## Exact next issue

- Title: `Public extractor recovery: switch from ffprobe JSON export_mvs to an alternate FFmpeg motion-vector surface`
- Changed variable: extractor surface only
- Why this is the next step:
  - environment and input contracts are already good enough to keep reusing
  - the unresolved question is whether a different FFmpeg-backed surface can expose coordinates for the same MP4 pair
- Success criterion:
  - at least one committed extraction path writes non-empty coordinate-bearing vectors for both public inputs
- Abort condition:
  - two materially different FFmpeg-backed extraction surfaces still fail on the same pair, proving the project must escalate beyond the current FFmpeg-side extractor family

## Guidance for the next agent

Start from the public pair and keep all non-extractor variables fixed. Do not switch datasets, do not start private validation, and do not add UI work until the baseline emits real vectors.

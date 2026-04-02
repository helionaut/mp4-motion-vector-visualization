# External Inputs Contract: MP4 Motion Vector Visualization

Status: Draft
Last Updated: bootstrap

## Project Intent

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Purpose

This document is the source of truth for every external, private, or user-supplied
input the project needs. Its job is to let agents move forward autonomously.

Rules:
- If raw assets already exist, the next step is to adapt them into the required
  tool format. That is implementation work, not a reason to stop.
- Only list something as "missing" if the source-of-truth asset, secret, or
  non-derivable fact is genuinely absent.
- Any required download, bootstrap, extraction, conversion, or preprocessing
  step should be scripted or documented in repo-local commands.

## Source Inputs

The workflow expects two MP4 source inputs for every comparison run.

Initial intake assumptions:
- baseline lane: use two public/shareable sample MP4s so extraction can be proven without waiting on private access
- validation lane: rerun the same workflow on user/private MP4s only after the public baseline is stable

Capture each source with:
- source name
- whether it is `public` or `private`
- current path or retrieval command
- codec/container notes if known
- trust/provenance notes

Current status:
- Public MP4 pair: selected as a deterministic synthetic fixture pair generated from FFmpeg lavfi sources
  - manifest: `manifests/public_known_good_baseline.json`
  - input A: `synthetic-grid` -> `datasets/fixtures/public-known-good/synthetic-grid.mp4`
  - input B: `synthetic-rotating-pattern` -> `datasets/fixtures/public-known-good/synthetic-rotating-pattern.mp4`
  - generator path: `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json`
  - provenance: both files are shareable/generated fixtures, not user data
- Private/user MP4 pair: not provided in this intake; only a blocker if HEL-152 begins and no private inputs exist then

## Prepared Artifacts

The downstream workflow should consume these prepared artifacts:

- normalized run manifest
  - generator: repo-local script or config created in HEL-150/HEL-151
  - output path: `manifests/<run-id>.json`
  - purpose: records the two MP4 inputs, extractor settings, and output artifact paths
- extracted motion-vector data
  - generator: baseline extractor command
  - output path: `reports/out/<run-id>/vectors/<input-name>.json` or equivalent stable format
  - purpose: per-frame vector data for rendering and comparison
- render artifacts
  - generator: baseline visualization step
  - output path: `reports/out/<run-id>/renders/`
  - purpose: visual overlays or frame summaries per input
- comparison artifact
  - generator: baseline comparison step
  - output path: `reports/out/<run-id>/comparison/`
  - purpose: side-by-side or aggregate comparison output

## Deterministic Paths

Use stable repo-local locations whenever possible.

Suggested conventions:
- raw/private inputs: `datasets/user/raw/`
- prepared/private artifacts: `datasets/user/prepared/`
- checked-in shareable fixtures: `datasets/fixtures/`
- calibration/config bundles: `configs/`
- manifests describing prepared runs: `manifests/`
- logs and reports: `logs/out/` and `reports/out/`

For shared-cache reuse on this project:
- reusable public or private media inputs should live under `/home/helionaut/srv/research-cache/18afd661ce11/datasets`
- heavy generated artifacts should live under `/home/helionaut/srv/research-cache/18afd661ce11/artifacts`
- repo-local paths should store manifests, scripts, and lightweight reports that describe how to reproduce those artifacts

## Bootstrap And Acquisition

HEL-150 should make these steps concrete:

1. generate the deterministic public MP4 pair from `manifests/public_known_good_baseline.json`
2. verify the generated files are readable with `ffprobe`
3. export motion-vector side data with `ffprobe -flags2 +export_mvs`
4. render one codecview overlay per input plus one SVG comparison summary
5. document how private/user inputs should be placed for the later validation lane

## Real Gaps

- The public baseline runner cannot execute on the current machine because the host lacks `docker`, `ffmpeg`, and `ffprobe`.
  - Why it matters: HEL-151 can only leave behind a reproducible failure artifact here, not a live success run.
  - Downstream impact: a Docker-capable host must rerun the committed command surface before HEL-152 should reuse the baseline.
- Private/user MP4 pair is not yet required for this intake ticket.
  - Why it is not a current blocker: HEL-152 is the first lane that should depend on those assets.

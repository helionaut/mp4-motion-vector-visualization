# Research Contract

Project: MP4 Motion Vector Visualization

## Strategic goal

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Current answer state

- Overall verdict: `public-baseline-failure-reproduced`
- Highest-value unanswered question: which extractor or FFmpeg invocation change is required when `ffprobe` exposes motion-vector side-data markers but omits the coordinate payload for the agreed public MP4 pair?

## Reusable baseline

- Known-good public baseline: `configs/input_sets/public-baseline.json` -> `manifests/public-baseline.json` prepared by `scripts/prepare_public_inputs.sh`, then executed by `scripts/public_baseline.py`
- Known-good private/user-data baseline: _not established yet_
- Reusable build/tooling baseline: repo-local Dockerfile plus `scripts/run_in_docker.sh` with shared cache mounts; live container proof still requires a Docker-capable host
- Shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`

## Intake translation

The intake resolves into one research spine:

1. define the experiment contract and acceptance boundary
2. lock a reproducible Docker environment
3. define and validate the two-MP4 input contract
4. prove a public extraction/render baseline
5. rerun on private data only after the public lane is stable
6. synthesize findings and recommend the next slice

This project should not branch into UI polish or speculative parser work until the public baseline proves that extracted motion vectors can be rendered and compared credibly.

## Baseline hypothesis

- Hypothesis: FFmpeg-exposed codec motion vectors are sufficient to build the first visualization and comparison workflow.
- Success criterion: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json` produces vector data plus render artifacts for the committed public MP4 pair.
- Abort condition: if the same command cannot produce vectors or renders on this stack, record the exact failure mode in `reports/out/public-baseline/` and move the changed variable to extractor selection instead of retrying blindly.

## Expected research artifacts

- a command or script that ingests two MP4 paths deterministically
- extracted vector data in a stable machine-readable format
- overlay and/or comparison images or video artifacts
- a short report describing what was proven, what remains open, and which variable changes next

## HEL-151 outcome on this machine

- Committed assets:
  - `manifests/public-baseline.json`
  - `scripts/public_baseline.py`
  - `reports/out/public-baseline/status.json`
  - `reports/out/public-baseline/report.md`
- What is proven here:
  - the public baseline reuses the established HEL-150 public input contract
  - the runner emits deterministic extraction, render, and comparison steps from that manifest
  - `scripts/prepare_public_inputs.sh` succeeds on this host and the baseline writes render artifacts for both public MP4 inputs
  - the failure is narrower than environment bootstrap: `ffprobe` marks `Motion vectors` side data on 714 frames per input, but the JSON payload omits coordinate arrays, so machine-readable vectors remain unavailable
- Changed variable recommended next:
  - extractor invocation/selection, not environment or input preparation

## Experiment ledger rules

Every research/build/run issue should leave behind a compact tactical + strategic handoff in this file or in a linked report:

- what is already proven
- what is still blocked
- what exact variable changes next
- what success would look like
- what abort condition ends the attempt
- which artifacts, binaries, datasets, or reports the next agent should reuse

Do not let the project drift into generic follow-up tickets. Every next issue should name the concrete stage and changed variable.

## Follow-up issue contract

Use this compact shape for future research follow-up issues:

### Strategic context
- one paragraph on why this step matters for the project hypothesis

### Tactical next step
- the one blocker or question this issue attacks directly

### Reuse from previous work
- committed scripts, reports, paths, binaries, datasets, or cache dirs the next agent should start from

### Changed variable
- the one variable that changes in this attempt

### Hypothesis
- what we expect to learn if this attempt succeeds or fails

### Success criterion
- the concrete observable result that counts as success

### Abort condition
- when to stop retrying and write up the blocker instead of looping

### Outputs
- which report, binary provenance, artifact, PR, or document must exist when the issue finishes

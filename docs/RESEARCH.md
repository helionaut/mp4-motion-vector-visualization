# Research Contract

Project: MP4 Motion Vector Visualization

## Strategic goal

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Current answer state

- Overall verdict: `open`
- Highest-value unanswered question: can the committed FFmpeg-side baseline command produce real artifacts on a Docker-capable machine, or does it fail in a reproducible way that changes the extractor variable?

## Reusable baseline

- Known-good public baseline: deterministic synthetic fixture pair defined in `manifests/public_known_good_baseline.json` and executed by `scripts/public_baseline.py`; this machine only proves the blocked runtime path because Docker/FFmpeg are unavailable locally
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
- Success criterion: `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json` produces vector data plus render artifacts for the committed synthetic public MP4 pair.
- Abort condition: if the same command cannot produce vectors or renders on a Docker-capable machine, record the exact failure mode in `reports/out/public-known-good-baseline/` and move the changed variable to extractor selection instead of retrying blindly.

## Expected research artifacts

- a command or script that ingests two MP4 paths deterministically
- extracted vector data in a stable machine-readable format
- overlay and/or comparison images or video artifacts
- a short report describing what was proven, what remains open, and which variable changes next

## HEL-151 outcome on this machine

- Committed assets:
  - `manifests/public_known_good_baseline.json`
  - `scripts/public_baseline.py`
  - `reports/out/public-known-good-baseline/status.json`
  - `reports/out/public-known-good-baseline/report.md`
- What is proven here:
  - the public baseline input pair is explicit and shareable
  - the runner emits deterministic generation, extraction, render, and comparison steps
  - the branch contains a machine-readable minimal reproducible failure for hosts without `ffmpeg`/`ffprobe`
- What still needs infrastructure:
  - a Docker-capable host must run the documented wrapper command so the baseline can produce real vectors and render artifacts

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

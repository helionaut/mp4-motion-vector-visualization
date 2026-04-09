# Research Contract

Project: MP4 Motion Vector Visualization

## Strategic goal

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Current answer state

- Overall verdict: `private-lane-proven-on-host-with-compact-summary-sidecars`
- Highest-value unanswered question: whether the public lane should be rerun on this same host so the repo also carries a refreshed public success artifact, not only the private success proof

## Reusable baseline

- Known-good public baseline: a truthful public success proof is still not established, but HEL-151 now publishes a reusable stronger failure boundary on branch `eugeniy/hel-151-public-known-good-baseline-mp4-motion-vector-visualization` / PR #5, and HEL-152 now carries the same runner locally: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json` writes render artifacts for both public MP4 inputs and ends at `motion-vector-payload-missing` with 714 frames of motion-vector side-data markers but zero exported vectors per input; PR #5 records that command as an expected-exit-`3` validation step
- Known-good private/user-data baseline: HEL-152 has now exercised the committed private validation path on a real local candidate pair via `scripts/run_private_validation.sh`; it staged the files into the shared cache, wrote `manifests/user-validation.json`, and reproduced the same blocker as the public lane: motion-vector side-data bytes exist, but the FFmpeg CLI path still emits zero coordinate-bearing vectors
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

## HEL-152 status in project context

- Private/user-data validation is now partially proven.
- HEL-152 is no longer blocked on missing private files; the private lane ran on a real candidate pair and reproduced the same unresolved extractor boundary as the public lane.
- The reusable private-data contract from `docs/INPUTS.md` is still valid:
  - raw inputs belong under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/<run-id>/`
  - prepared metadata belongs under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/prepared/<run-id>/`
  - the same manifest shape can be reused once secure provenance replaces public `source_url` fields
- Do not spend the next issue on more private-data reruns until the extractor lane can produce non-empty machine-readable vectors.

## HEL-153 synthesis

### What is proven

- The project intent is stable: ingest two MP4 files, extract codec motion vectors, and visualize/compare them reproducibly.
- The environment contract is established in `docs/ENVIRONMENT.md` around the repo-local Docker wrapper and shared cache root `/home/helionaut/srv/research-cache/18afd661ce11`.
- The input contract is established in `docs/INPUTS.md` for the public Big Buck Bunny pair and for the future private-data lane.
- The public baseline command surface is fixed and reproducible:
  - `scripts/prepare_public_inputs.sh`
  - `python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`
- The public baseline successfully:
  - prepares and fingerprints the agreed public MP4 pair
  - records ffprobe sidecars and a normalized manifest
  - renders codecview overlay artifacts for both inputs
  - writes a compact failure report under `reports/out/public-baseline/`
- The observed failure is specific, reproducible, and narrower than environment or input setup:
  - `ffprobe` reports `Motion vectors` side-data markers on 714 frames for each public input
  - the JSON payload still contains zero coordinate arrays, so `frames_with_vectors=0` and `total_vectors=0` for both files

### What is blocked

- The workflow does not yet meet the core project hypothesis because no stage produces non-empty machine-readable motion vectors.
- Without vector payloads, the comparison lane cannot progress beyond codecview renders into a credible vector-backed comparison artifact.
- A private/user-data rerun would not answer a new question yet; it would mainly repeat the same extractor failure on a different input pair.
- Live Docker runtime proof is still unverified on this machine because the host lacks a `docker` CLI, but that is not the blocker that stopped the public baseline run on host tooling.

### Exact next issue

- Recommended next issue title: `Public extractor recovery: switch from ffprobe JSON export_mvs to FFmpeg -export_side_data mvs on the prepared public baseline`
- Strategic context:
  - the project is blocked on extraction viability, not on environment bootstrap, input preparation, or UI work
- Tactical next step:
  - rerun the public Big Buck Bunny baseline while changing only the extractor surface from the current `ffprobe -flags2 +export_mvs -show_frames -of json` path to an FFmpeg decode-path attempt using `-export_side_data mvs`
- Reuse from previous work:
  - `manifests/public-baseline.json`
  - `scripts/prepare_public_inputs.sh`
  - `scripts/public_baseline.py`
  - `reports/out/public-baseline/status.json`
  - `reports/out/public-baseline/report.md`
  - `/home/helionaut/srv/research-cache/18afd661ce11`
- Changed variable:
  - extractor surface only, specifically moving away from the current `ffprobe -flags2 +export_mvs -show_frames -print_format json` path to the FFmpeg decode surface that exports `mvs` side data
- Hypothesis:
  - the FFmpeg decode path with `-export_side_data mvs` can expose per-frame vector coordinates for the same public MP4 pair without changing inputs, Docker contract, or cache layout
- Success criterion:
  - the rerun publishes one deterministic command, a machine-readable runtime progress artifact with real counters, and either non-empty vector artifacts for at least one public input plus refreshed render/comparison evidence or a tighter truthful failure boundary tied to the FFmpeg `-export_side_data mvs` surface
- Abort condition:
  - if the `-export_side_data mvs` attempt still yields zero vectors or unsupported output for the same public pair, stop and record that exact boundary without reopening private/user-data validation
- Outputs:
  - updated extractor command or script
  - updated `reports/out/public-baseline/` evidence
  - a focused handoff that says what shipped in this slice, what remains blocked in the original request, and whether Docker-capable infrastructure is still required for a live container proof

## HEL-155 outcome

### What is proven

- The prepared public Big Buck Bunny pair still reproduces cleanly under the existing manifest, cache layout, and codecview render path.
- `ffmpeg -export_side_data +mvs -i <input> -vf showinfo -f null -` surfaces motion-vector side-data bytes on the public baseline even though the earlier `ffprobe -flags2 +export_mvs -show_frames -of json` path only exposed empty vector arrays.
- The decode-path rerun wrote a machine-readable runtime progress artifact at `.symphony/progress/HEL-155.json` and refreshed the public-baseline evidence under `reports/out/public-baseline/`.
- The new tighter boundary is specific and measured:
  - `bbb_480p_30s`: 714/720 frames with motion-vector side data, `66,011,680` total payload bytes
  - `bbb_1080p_30s`: 714/720 frames with motion-vector side data, `337,375,720` total payload bytes
  - both inputs still report `frames_with_vectors=0` and `total_vectors=0` because the FFmpeg CLI decode path does not serialize coordinate-bearing vectors

### What is blocked

- The public baseline now proves the decoder can surface motion-vector side-data payloads, but the committed CLI path still cannot turn those payload bytes into machine-readable coordinates.
- This means the original project ask is still not fully proven: the workflow can render codecview overlays and count payload bytes, but it still cannot publish coordinate-bearing motion-vector artifacts for comparison.
- Live Docker validation is still blocked on this machine because `docker` is unavailable, so the repo carries the command surface but not a locally executed container proof.

### Exact next issue

- Recommended next issue title: `Public extractor recovery: serialize FFmpeg motion-vector side data into coordinates on the prepared public baseline`
- Strategic context:
  - HEL-155 narrowed the blocker from "maybe no motion vectors are exported" to "motion-vector side-data bytes exist, but the current CLI surface does not serialize coordinates"
- Tactical next step:
  - keep the prepared public pair, Docker contract, and render/comparison paths fixed while replacing only the coordinate-serialization surface, for example with FFmpeg's `extract_mvs` example or a small libavcodec-backed helper
- Reuse from previous work:
  - `manifests/public-baseline.json`
  - `scripts/public_baseline.py`
  - `reports/out/public-baseline/status.json`
  - `reports/out/public-baseline/comparison/summary.json`
  - `reports/out/public-baseline/vectors/*.ffmpeg-showinfo.log`
  - `.symphony/progress/HEL-155.json`
  - `/home/helionaut/srv/research-cache/18afd661ce11`
- Changed variable:
  - coordinate-serialization surface only
- Hypothesis:
  - a libavcodec-backed extractor can reuse the now-proven FFmpeg motion-vector side-data payloads and emit non-empty coordinate-bearing vectors for the same public pair
- Success criterion:
  - the public baseline rerun writes non-empty machine-readable coordinate vectors for at least one input while keeping the manifest shape, prepared inputs, Docker contract, and output locations stable
- Abort condition:
  - if a library-level extractor still cannot serialize coordinate-bearing vectors from the same FFmpeg side-data payloads, stop and record that the project is blocked beyond the current FFmpeg extractor family
- Outputs:
  - one deterministic coordinate-serialization command or helper
  - refreshed public-baseline vector/comparison evidence
  - an updated handoff that says whether the project can finally reopen the private-data lane

## HEL-156 outcome

### What shipped

- The repo now carries a minimal host-side extractor at `tools/host_libavcodec_mv_extractor.c` that targets `AV_FRAME_DATA_MOTION_VECTORS` through `libavformat` / `libavcodec` / `libavutil`.
- `scripts/bootstrap_host_libavcodec.sh` provides the explicit host bootstrap/build contract for this slice and fails with a specific message when the required FFmpeg development metadata is unavailable.
- `scripts/public_baseline.py` now uses that host extractor surface for HEL-156, keeps the prepared public manifest and codecview render path stable, and writes host-slice progress/status artifacts to `.symphony/progress/HEL-156.json` plus `reports/out/public-baseline/status.json`.

### What is proven

- The changed variable stayed narrow: only the coordinate-serialization surface moved from the FFmpeg CLI boundary to a repo-local host `libavcodec` helper.
- The prepared public baseline inputs, manifests, shared cache paths, and render/comparison directories remain the reuse surface.
- The current machine reaches a tighter truthful runtime boundary than HEL-155:
  - static `ffmpeg` / `ffprobe` binaries are present in the shared cache
  - `gcc` is present
  - the host does not expose `libavformat`, `libavcodec`, or `libavutil` through `pkg-config`
  - the host-run extractor therefore cannot be compiled here, and the blocked state is now explicit: `host-libavcodec-dev-surface-missing`

### What is still blocked

- Coordinate-bearing vectors are still not proven end-to-end because the current machine cannot compile the new extractor against FFmpeg development libraries.
- This means the original ingest/extract/compare ask is still unresolved; the project still lacks a validated coordinate-vector artifact on the prepared public pair.
- The Docker contract is still documented but not live-proven on this host because Docker remains unavailable here.

### Exact next issue

- Recommended next issue title: `Host libavcodec extractor validation: rerun HEL-156 on a machine with FFmpeg development packages`
- Strategic context:
  - HEL-156 replaced the extractor surface in code, but the current host disproved the assumed runtime contract before coordinate serialization could be executed
- Tactical next step:
  - run the committed HEL-156 host bootstrap and baseline command unchanged on a machine where `pkg-config --exists libavformat libavcodec libavutil` succeeds
- Reuse from previous work:
  - `tools/host_libavcodec_mv_extractor.c`
  - `scripts/bootstrap_host_libavcodec.sh`
  - `scripts/public_baseline.py`
  - `manifests/public-baseline.json`
  - `.symphony/progress/HEL-156.json`
  - `reports/out/public-baseline/status.json`
  - `/home/helionaut/srv/research-cache/18afd661ce11`
- Changed variable:
  - runtime environment only, specifically moving from the current host with missing FFmpeg dev metadata to one with the required development surface installed
- Hypothesis:
  - on a correctly provisioned host, the committed libavcodec extractor will compile and reveal whether `AV_FRAME_DATA_MOTION_VECTORS` contains non-empty coordinate vectors for the prepared public pair
- Success criterion:
  - the unchanged HEL-156 command surface either emits non-empty coordinate vectors plus refreshed comparison artifacts or records a tighter library-level decode boundary after the extractor actually runs
- Abort condition:
  - if the extractor compiles and still emits zero vectors on the same prepared public pair, stop and record that exact library/runtime boundary instead of reopening private validation
- Outputs:
  - compile/run evidence for the committed host extractor
  - refreshed vector/comparison artifacts or a tighter library-level blocker report

## HEL-157 outcome

### What shipped

- `tools/host_libavcodec_mv_extractor.c` now writes a compact `<vectors>.summary.json` sidecar alongside the full coordinate-vector JSON artifact.
- `scripts/public_baseline.py` now requests that sidecar through `--summary-output`, prefers it during readback, and falls back to the full vector JSON only when the sidecar is absent.
- The runner now writes manifest-aware report/status text instead of hardcoding the stale HEL-156 public-baseline command narrative into every run.

### What is proven

- The changed variable stayed narrow: only the artifact/summarization path changed after HEL-156's host extractor and the staged private pair were already fixed.
- On this WSL machine, the private lane now completes end-to-end against the staged shared-cache pair under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/user-validation/`.
- The previous multi-GB Python bottleneck is removed in practice:
  - `reports/out/user-validation/vectors/input_a.json`: `3,284,375,590` bytes
  - `reports/out/user-validation/vectors/input_b.json`: `3,284,046,880` bytes
  - Python advanced past those artifacts by consuming the compact sidecars instead of `json.loads(...)` on the full files
- The private run now publishes truthful coordinate-vector evidence for both inputs:
  - `input_a`: `11,597,086` vectors across `253/270` frames
  - `input_b`: `11,590,595` vectors across `253/270` frames
- The comparison lane is now proven on the private inputs as well:
  - `reports/out/user-validation/comparison/summary.json`
  - `reports/out/user-validation/comparison/summary.svg`
  - `reports/out/user-validation/status.json`
  - `reports/out/user-validation/report.md`

### What is still open

- HEL-157 proves the original ingest/extract/compare ask on the private lane for this host, but the repo history still carries a stale public-host blocker narrative from HEL-156 until the public artifacts are refreshed from the now-working host.
- Docker runtime proof is still not part of this slice; the successful proof here is host-based on the provisioned WSL machine.

### Exact next issue

- Recommended next issue title: `Public artifact refresh: rerun the host libavcodec baseline with compact summary sidecars on the provisioned WSL host`
- Strategic context:
  - the private lane is now truthfully proven, but repo-facing public artifacts and docs still overemphasize the superseded HEL-156 machine blocker
- Tactical next step:
  - rerun the unchanged public pair on this same host so `reports/out/public-baseline/` reflects the now-proven host extractor plus compact-summary contract
- Reuse from previous work:
  - `tools/host_libavcodec_mv_extractor.c`
  - `scripts/public_baseline.py`
  - `scripts/bootstrap_host_libavcodec.sh`
  - `manifests/public-baseline.json`
  - `reports/out/user-validation/`
  - `.symphony/validation/HEL-157.json`
  - `/home/helionaut/srv/research-cache/18afd661ce11`
- Changed variable:
  - report/artifact refresh target only, moving from the private validation manifest back to the prepared public manifest on the same working host
- Hypothesis:
  - the same host that completed HEL-157 private validation will also refresh the public evidence without reopening the earlier environment debate
- Success criterion:
  - the public rerun completes with non-empty coordinate-vector evidence plus refreshed comparison/report artifacts on this same host
- Abort condition:
  - if the public rerun unexpectedly fails on this host, stop and record the exact divergence from the successful private run instead of speculating
- Outputs:
  - refreshed `reports/out/public-baseline/` evidence
  - updated docs/handoff copy that explicitly marks the HEL-156 blocker narrative as superseded

## HEL-163 outcome

### What shipped

- `scripts/render_dense_flow.py` renders a dense optical-flow-style artifact directly from the host extractor's coordinate-vector JSON.
- `scripts/public_baseline.py` now invokes that renderer per input so the baseline can emit both the older `codecview` still and a dense raw/overlay visualization slice.
- The renderer writes a representative-frame `summary.json`, a raw dense map, and an overlay image with a magnitude scale plus a direction legend.

### What is proven

- On this WSL host, `scripts/bootstrap_host_libavcodec.sh --output build/host/libavcodec_mv_extractor` now succeeds, which supersedes the earlier local blocker that claimed FFmpeg development metadata was unavailable.
- A real public sample clip now yields dense codec-grid evidence with reviewable artifacts under `reports/out/hel-163-dense-flow/bbb_480p_sample/`.
- The dense view is truthful about codec limits: coverage is dense across the exposed block grid (`8x8` and `16x16` on the sample), not a fabricated per-pixel flow field.

### What is still open

- This slice proves artifact generation on a sample clip and wires the public baseline to produce dense-flow outputs, but it does not yet refresh the full committed `reports/out/public-baseline/` evidence set on the current host.
- The browser demo remains the older decoded-frame optical-flow approximation; HEL-163 does not convert the browser UI into a codec-vector player.

### Exact next issue

- Recommended next issue title: `Public baseline refresh: regenerate full dense codec-flow artifacts from the prepared public pair`
- Strategic context:
  - the renderer and extractor surface are now working locally, so the next valuable step is to refresh the canonical public evidence instead of extending a separate demo surface
- Tactical next step:
  - rerun `scripts/public_baseline.py run --manifest manifests/public-baseline.json` on this host and publish the resulting dense-flow artifacts alongside refreshed comparison/report evidence
- Changed variable:
  - artifact refresh scope only, from sample-clip proof to the full prepared public pair
- Hypothesis:
  - the same working host extractor surface will regenerate the public baseline with dense codec-flow artifacts without reopening the earlier environment blocker
- Success criterion:
  - `reports/out/public-baseline/` contains refreshed dense raw/overlay outputs plus updated report/status evidence that matches the current host reality
- Abort condition:
  - if the full public rerun fails despite the working sample proof, stop and record the exact divergence between sample-clip success and full-baseline behavior
- Outputs:
  - refreshed full-run dense-flow artifacts
  - updated public report/status/handoff evidence

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

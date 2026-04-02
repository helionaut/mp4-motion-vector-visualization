# HEL-152 Handoff

Date: 2026-04-02
Issue: `HEL-152`

## Strategic context

HEL-152 is the private-data validation lane. It only makes sense after HEL-151 leaves a credible, reusable public baseline that extracts motion vectors and produces comparison artifacts from the committed environment and input contracts.

## Tactical result from this pass

This pass made HEL-152 self-contained for the published baseline surface: the branch now carries the HEL-151 public runner, reproduces the same local `motion-vector-payload-missing` failure boundary without Docker, and exposes a one-command private validation wrapper. The remaining missing fact is the actual user MP4 pair.

## What was checked

- `.bootstrap/project.json`, `.symphony/session.json`, and the narrow contract docs in `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`
- HEL-151 and HEL-152 Linear issue state and workpad history
- GitHub PR state for `helionaut/mp4-motion-vector-visualization`
- shared research cache contents under `/home/helionaut/srv/research-cache/18afd661ce11`
- local tool availability for `docker`, `ffmpeg`, and `ffprobe`

## Findings

1. HEL-151 is still `In Progress`.
2. HEL-151 now has a published remote branch `eugeniy/hel-151-public-known-good-baseline-mp4-motion-vector-visualization` and open PR #5 (`Reproduce public MP4 baseline extractor failure`) at head `34cd50a32f7c7e0c3a6c20f5d7dc864a11d50a53`.
3. PR #5 publishes a stronger reusable public failure boundary instead of the older missing-runtime-only report.
4. Its committed `reports/out/public-baseline/status.json` records `motion-vector-payload-missing` with the exact command surface `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`, and the PR body already records that same command as an expected-exit-`3` validation step.
5. The committed report says both public inputs produced render artifacts and `ffprobe` side-data markers on 714 frames each, but zero exported motion-vector payload coordinates.
6. `scripts/bootstrap_media_tools.sh` now proves this host can bootstrap runnable static `ffprobe` and `ffmpeg` binaries under the shared toolchain cache even though no system binaries are on `PATH`.
7. HEL-152 now carries `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, the committed public blocked-run report, and the focused tests needed to execute the published baseline surface from this branch.
8. Running `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json` on this host reproduces the same expected blocked boundary with exit `3` and refreshed render/report artifacts, so Docker is no longer required to prove that public baseline surface locally.
9. HEL-152 now has a committed private staging and rerun path via `configs/input_sets/private-template.json`, `scripts/prepare_private_inputs.sh`, and `scripts/run_private_validation.sh`, so the next pass does not need to assemble the private lane manually once the user MP4 pair arrives.
10. A truthful public success baseline still does not exist, and there is still no `datasets/user/` tree for HEL-152 to run against.

## Experiment contract for the next pass

- Changed variable: input visibility
- Hypothesis: rerunning the now-published public failure boundary on user MP4s will show whether `motion-vector-payload-missing` is specific to the public Big Buck Bunny pair or reproduces on private inputs too
- Success criterion: a private-data rerun uses HEL-151's published command surface unchanged, records whether user files also expose side-data markers with zero vectors, and leaves comparable status/report artifacts
- Abort condition: if the user dataset is still absent, stop again and keep the blocker on input availability rather than inventing substitute media

## Reuse from previous work

- environment wrapper: `scripts/run_in_docker.sh`
- environment contract: `docs/ENVIRONMENT.md`
- public and private input contract: `docs/INPUTS.md`, `scripts/prepare_inputs.py`, `scripts/prepare_private_inputs.sh`, `scripts/run_private_validation.sh`, `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, `configs/input_sets/private-template.json`, `manifests/public-baseline.json`
- shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`
- HEL-151 published branch `eugeniy/hel-151-public-known-good-baseline-mp4-motion-vector-visualization` and open PR #5 at `34cd50a32f7c7e0c3a6c20f5d7dc864a11d50a53`
- committed public failure artifacts in `reports/out/public-baseline/`
- public command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`

## Next recommended slice

Provision the actual user MP4 pair for HEL-152 and run `scripts/run_private_validation.sh` on this host to determine whether private inputs also hit `motion-vector-payload-missing` or expose a different blocker.

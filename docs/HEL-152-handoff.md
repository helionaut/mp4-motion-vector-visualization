# HEL-152 Handoff

Date: 2026-04-02
Issue: `HEL-152`

## Strategic context

HEL-152 is the private-data validation lane. It only makes sense after HEL-151 leaves a credible, reusable public baseline that extracts motion vectors and produces comparison artifacts from the committed environment and input contracts.

## Tactical result from this pass

This pass confirmed that HEL-151 now publishes a reusable public failure boundary, proved that the committed host media bootstrap works locally, and added a one-command private staging wrapper. A truthful public success proof still does not exist and the actual user MP4 pair is still absent.

## What was checked

- `.bootstrap/project.json`, `.symphony/session.json`, and the narrow contract docs in `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`
- HEL-151 and HEL-152 Linear issue state and workpad history
- GitHub PR state for `helionaut/mp4-motion-vector-visualization`
- shared research cache contents under `/home/helionaut/srv/research-cache/18afd661ce11`
- local tool availability for `docker`, `ffmpeg`, and `ffprobe`

## Findings

1. HEL-151 is still `In Progress`.
2. HEL-151 now has a published remote branch and draft PR #5 (`Reproduce public MP4 baseline extractor failure`) at head `34cd50a32f7c7e0c3a6c20f5d7dc864a11d50a53`.
3. PR #5 now publishes a stronger reusable public failure boundary instead of the older missing-runtime-only report.
4. Its committed `reports/out/public-baseline/status.json` records `motion-vector-payload-missing` with the exact command surface `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`.
5. The committed report says both public inputs produced render artifacts and `ffprobe` side-data markers on 714 frames each, but zero exported motion-vector payload coordinates.
6. `scripts/bootstrap_media_tools.sh` now proves this host can bootstrap runnable static `ffprobe` and `ffmpeg` binaries under the shared toolchain cache even though no system binaries are on `PATH`.
7. HEL-152 now has a committed private staging path via `configs/input_sets/private-template.json` and `scripts/prepare_private_inputs.sh`, so the repo no longer needs a new adapter before the user MP4 pair arrives.
8. A truthful public success baseline still does not exist, and there is still no `datasets/user/` tree for HEL-152 to run against.
9. Docker is still unavailable on this host, so this machine still cannot exercise the repo's Docker environment contract; however, private manifest preparation itself is no longer blocked on missing host media binaries.

## Experiment contract for the next pass

- Changed variable: input visibility
- Hypothesis: rerunning the now-published public failure boundary on user MP4s will show whether `motion-vector-payload-missing` is specific to the public Big Buck Bunny pair or reproduces on private inputs too
- Success criterion: a private-data rerun uses HEL-151's published command surface unchanged, records whether user files also expose side-data markers with zero vectors, and leaves comparable status/report artifacts
- Abort condition: if the current machine still cannot execute the required toolchain or the user dataset is still absent, stop again and keep the blocker on infrastructure/input availability rather than inventing a different lane

## Reuse from previous work

- environment wrapper: `scripts/run_in_docker.sh`
- environment contract: `docs/ENVIRONMENT.md`
- public and private input contract: `docs/INPUTS.md`, `scripts/prepare_inputs.py`, `scripts/prepare_private_inputs.sh`, `configs/input_sets/private-template.json`, `manifests/public-baseline.json`
- shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`
- HEL-151 draft PR #5 at `34cd50a32f7c7e0c3a6c20f5d7dc864a11d50a53`
- committed public failure artifacts in `reports/out/public-baseline/`
- public command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`

## Next recommended slice

Provision the actual user MP4 pair for HEL-152, stage the files with `scripts/prepare_private_inputs.sh`, and then on a Docker-capable machine reuse HEL-151's published public command surface unchanged to determine whether private inputs also hit `motion-vector-payload-missing` or expose a different blocker.

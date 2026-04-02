# HEL-152 Handoff

Date: 2026-04-02
Issue: `HEL-152`

## Strategic context

HEL-152 is the private-data validation lane. It only makes sense after the public baseline leaves a credible, reusable extraction/render surface in the committed environment and input contracts.

## Tactical result from this pass

This pass rechecked the published HEL-152 validation lane against the current workspace state: local and published branch heads both resolve to PR #6 head `3e2c7bb`, the HEL-155 FFmpeg decode-path baseline remains the committed surface this lane must reuse, and the one-command private validation wrapper is still correctly blocked by a machine-readable `missing-user-inputs` result until the real user MP4 pair is staged.

## What was checked

- `.bootstrap/project.json`, `.symphony/session.json`, and the narrow contract docs in `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`
- HEL-151, HEL-152, and HEL-155 issue/PR state
- GitHub PR state for `helionaut/mp4-motion-vector-visualization`
- shared research cache contents under `/home/helionaut/srv/research-cache/18afd661ce11`
- local tool availability for `docker`, `ffmpeg`, and `ffprobe`

## Findings

1. PR #6 (`HEL-152: self-contain baseline and private validation`) is still open and draft on GitHub at head `3e2c7bb0fba22e8de3d9f8b02b95c11bda599795`.
2. The local workspace head and `origin/eugeniy/hel-152-user-data-validation-lane-mp4-motion-vector-visualization` both resolve to `3e2c7bb`, so there is no unpublished local divergence to repair before the next rerun.
3. HEL-152 still inherits the HEL-155 public baseline surface from `origin/main`, not the older HEL-151 `ffprobe` boundary.
4. The committed `reports/out/public-baseline/status.json` records the current public-lane blocker `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors`.
5. That committed report proves the FFmpeg decode path surfaces motion-vector side-data bytes on 714/720 frames for both public inputs, but still serializes zero coordinate-bearing vectors.
6. `scripts/bootstrap_media_tools.sh` still proves this host can bootstrap runnable static `ffprobe` and `ffmpeg` binaries under the shared toolchain cache even though no system binaries are on `PATH`.
7. HEL-152 carries `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, the committed HEL-155 public blocked-run report, and the focused tests needed to execute the current published baseline surface from this branch.
8. The existing aggregate local validation artifact is still green on `3e2c7bb`: docs/contracts passed, tests passed, `scripts/validate_public_baseline.py` passed, and `scripts/run_private_validation.sh` still exits `2` with the machine-readable `missing-user-inputs` artifact until real user media is staged.
9. HEL-152 still has the committed private staging and rerun path via `configs/input_sets/private-template.json`, `scripts/prepare_private_inputs.sh`, `scripts/run_private_validation.sh`, and `scripts/validate_private_input_config.py`, so the next pass does not need to assemble the private lane manually once the user MP4 pair arrives.
10. `find /home/helionaut/srv/research-cache/18afd661ce11/datasets/user -maxdepth 4 -type f` returns no staged private files, so the private rerun cannot start truthfully on this machine yet.

## Experiment contract for the next pass

- Changed variable: input visibility only
- Hypothesis: rerunning the now-published FFmpeg decode-path public boundary on user MP4s will show whether the CLI coordinate-serialization blocker is specific to the public Big Buck Bunny pair or also appears on private inputs
- Success criterion: a private-data rerun uses the current published command surface unchanged, records whether user files also expose motion-vector side-data bytes with zero coordinate vectors, and leaves comparable status/report artifacts
- Abort condition: if the user dataset is still absent, stop again and keep the blocker on input availability rather than inventing substitute media

## Reuse from previous work

- environment wrapper: `scripts/run_in_docker.sh`
- environment contract: `docs/ENVIRONMENT.md`
- public and private input contract: `docs/INPUTS.md`, `scripts/prepare_inputs.py`, `scripts/prepare_private_inputs.sh`, `scripts/run_private_validation.sh`, `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, `configs/input_sets/private-template.json`, `manifests/public-baseline.json`
- shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`
- HEL-155 landed on `origin/main` as commit `59e42f64416d7aa0a4b768f4f1885bc525f0b7c4`
- current review branch / PR: `eugeniy/hel-152-user-data-validation-lane-mp4-motion-vector-visualization` / PR #6 at `3e2c7bb0fba22e8de3d9f8b02b95c11bda599795`
- committed public failure artifacts in `reports/out/public-baseline/`
- public command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`

## Next recommended slice

Provision the actual user MP4 pair for HEL-152 and run `scripts/run_private_validation.sh` on this host to determine whether private inputs also hit `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors` or expose a different blocker.

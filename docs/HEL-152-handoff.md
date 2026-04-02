# HEL-152 Handoff

Date: 2026-04-02
Issue: `HEL-152`

## Strategic context

HEL-152 is the private-data validation lane. It only makes sense after the public baseline leaves a credible, reusable extraction/render surface in the committed environment and input contracts.

## Tactical result from this pass

This pass keeps HEL-152 aligned with the latest published public baseline surface: the branch now carries the HEL-155 FFmpeg decode-path runner and evidence, local and remote validation are green on PR #6 head `980c0e6`, and the one-command private validation wrapper still fails early with a machine-readable `missing-user-inputs` blocker until the real user MP4 pair is staged.

## What was checked

- `.bootstrap/project.json`, `.symphony/session.json`, and the narrow contract docs in `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`
- HEL-151, HEL-152, and HEL-155 issue/PR state
- GitHub PR state for `helionaut/mp4-motion-vector-visualization`
- shared research cache contents under `/home/helionaut/srv/research-cache/18afd661ce11`
- local tool availability for `docker`, `ffmpeg`, and `ffprobe`

## Findings

1. PR #6 (`HEL-152: self-contain baseline and private validation`) is open, draft, and clean on GitHub at head `980c0e6a5ff854dd4adf775dc2fb7598d31f737b`.
2. The visible GitHub Actions runs for `980c0e6` are complete and successful:
   - `Intake Docs CI`: success (`23918409672`)
   - `Intake Docs CI`: success (`23918407347`)
3. HEL-152 now inherits the newer HEL-155 public baseline surface from `origin/main`, not the older HEL-151 `ffprobe` boundary.
4. The committed `reports/out/public-baseline/status.json` now records the tighter blocker `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors` instead of `motion-vector-payload-missing`.
5. That committed report proves the FFmpeg decode path surfaces motion-vector side-data bytes on 714/720 frames for both public inputs, but still serializes zero coordinate-bearing vectors.
6. `scripts/bootstrap_media_tools.sh` still proves this host can bootstrap runnable static `ffprobe` and `ffmpeg` binaries under the shared toolchain cache even though no system binaries are on `PATH`.
7. HEL-152 carries `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, the committed HEL-155 public blocked-run report, and the focused tests needed to execute the current published baseline surface from this branch.
8. Aggregate local validation is green on `980c0e6`: docs/contracts passed, 13 tests passed, `scripts/validate_public_baseline.py` passed, and `scripts/run_private_validation.sh` still exits `2` with the machine-readable `missing-user-inputs` artifact.
9. HEL-152 still has the committed private staging and rerun path via `configs/input_sets/private-template.json`, `scripts/prepare_private_inputs.sh`, `scripts/run_private_validation.sh`, and `scripts/validate_private_input_config.py`, so the next pass does not need to assemble the private lane manually once the user MP4 pair arrives.
10. There is still no staged file anywhere under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/`, so the private rerun cannot start truthfully.

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
- current review branch / PR: `eugeniy/hel-152-user-data-validation-lane-mp4-motion-vector-visualization` / PR #6 at `980c0e6a5ff854dd4adf775dc2fb7598d31f737b`
- committed public failure artifacts in `reports/out/public-baseline/`
- public command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`

## Next recommended slice

Provision the actual user MP4 pair for HEL-152 and run `scripts/run_private_validation.sh` on this host to determine whether private inputs also hit `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors` or expose a different blocker.

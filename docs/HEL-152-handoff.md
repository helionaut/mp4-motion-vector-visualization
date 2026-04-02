# HEL-152 Handoff

Date: 2026-04-02
Issue: `HEL-152`

## Strategic context

HEL-152 is the private-data validation lane. It only makes sense after the public baseline leaves a credible, reusable extraction/render surface in the committed environment and input contracts.

## Tactical result from this pass

This pass reopened the private-data lane with a real candidate MP4 pair found on the local machine: the unchanged `scripts/run_private_validation.sh` wrapper staged `/home/helionaut/.openclaw/workspace/downloads/insta360-b87308a3/{00.mp4,10.mp4}` into the shared cache, wrote `manifests/user-validation.json`, and reproduced the same downstream blocker as the public HEL-155 lane on PR #6 head `4797ee0`.

## What was checked

- `.bootstrap/project.json`, `.symphony/session.json`, and the narrow contract docs in `docs/ENVIRONMENT.md`, `docs/INPUTS.md`, and `docs/RESEARCH.md`
- HEL-151, HEL-152, and HEL-155 issue/PR state
- GitHub PR state for `helionaut/mp4-motion-vector-visualization`
- shared research cache contents under `/home/helionaut/srv/research-cache/18afd661ce11`
- local candidate media under `/home/helionaut/.openclaw/workspace/downloads/insta360-b87308a3/`
- local tool availability for `docker`, `ffmpeg`, and `ffprobe`

## Findings

1. PR #6 (`HEL-152: self-contain baseline and private validation`) is still open and draft on GitHub at head `4797ee0d2b52974b3a49a955b32fa52ba634f90a`.
2. The local workspace head and `origin/eugeniy/hel-152-user-data-validation-lane-mp4-motion-vector-visualization` both resolve to `4797ee0`, so there is no unpublished local divergence to repair.
3. HEL-152 still inherits the HEL-155 public baseline surface from `origin/main`, not the older HEL-151 `ffprobe` boundary.
4. The committed `reports/out/public-baseline/status.json` records the current public-lane blocker `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors`.
5. That committed report proves the FFmpeg decode path surfaces motion-vector side-data bytes on 714/720 frames for both public inputs, but still serializes zero coordinate-bearing vectors.
6. `scripts/bootstrap_media_tools.sh` still proves this host can bootstrap runnable static `ffprobe` and `ffmpeg` binaries under the shared toolchain cache even though no system binaries are on `PATH`.
7. HEL-152 carries `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, the committed HEL-155 public blocked-run report, and the focused tests needed to execute the current published baseline surface from this branch.
8. The last aggregate green validation artifact is still `.symphony/validation/HEL-152.json` on `3e2c7bb`: docs/contracts passed, tests passed, `scripts/validate_public_baseline.py` passed, and the then-current private wrapper correctly stopped at the old `missing-user-inputs` blocker.
9. A new workspace-local private config at `.symphony/private-inputs/insta360-candidate.json` pointed the unchanged private wrapper at the discovered candidate pair `/home/helionaut/.openclaw/workspace/downloads/insta360-b87308a3/{00.mp4,10.mp4}`.
10. `scripts/run_private_validation.sh` staged those files into `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/user-validation/`, wrote ffprobe sidecars under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/prepared/user-validation/probe/`, and emitted `manifests/user-validation.json`.
11. The private rerun produced fresh local artifacts under `reports/out/user-validation/` and ended with the same blocker as the public lane: `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors`.
12. The private metrics match that tighter boundary rather than the old missing-input stop:
    - `input_a`: `253/270` frames with motion-vector side-data, `463,855,680` payload bytes, `0` vectors
    - `input_b`: `253/270` frames with motion-vector side-data, `463,608,720` payload bytes, `0` vectors
13. HEL-152 is no longer blocked on input availability; it is now blocked on the same coordinate-serialization limit already observed on the public FFmpeg CLI decode path.

## Experiment contract for the next pass

- Changed variable: private input pair only
- Hypothesis: rerunning the published FFmpeg decode-path boundary on real private MP4s will show whether the coordinate-serialization blocker is specific to the public Big Buck Bunny pair or general to this CLI extractor surface
- Success criterion: the unchanged private wrapper stages a real private pair, produces a private manifest plus report artifacts, and records whether the user files also expose motion-vector side-data bytes with zero coordinate vectors
- Abort condition: if the candidate files are unreadable, invalid, or clearly not the intended private lane inputs, stop and keep the blocker on input identification rather than changing the extractor surface

## Reuse from previous work

- environment wrapper: `scripts/run_in_docker.sh`
- environment contract: `docs/ENVIRONMENT.md`
- public and private input contract: `docs/INPUTS.md`, `scripts/prepare_inputs.py`, `scripts/prepare_private_inputs.sh`, `scripts/run_private_validation.sh`, `scripts/public_baseline.py`, `scripts/validate_public_baseline.py`, `configs/input_sets/private-template.json`, `manifests/public-baseline.json`
- shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`
- HEL-155 landed on `origin/main` as commit `59e42f64416d7aa0a4b768f4f1885bc525f0b7c4`
- current review branch / PR: `eugeniy/hel-152-user-data-validation-lane-mp4-motion-vector-visualization` / PR #6 at `4797ee0d2b52974b3a49a955b32fa52ba634f90a`
- committed public failure artifacts in `reports/out/public-baseline/`
- private rerun artifacts kept local in `manifests/user-validation.json`, `reports/out/user-validation/`, and `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/{raw,prepared}/user-validation/`
- public command surface: `scripts/prepare_public_inputs.sh && python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json --progress-artifact .symphony/progress/HEL-155.json`

## Next recommended slice

Do not spend another pass on private-input staging. The next slice should attack coordinate serialization directly, because both the public pair and the private candidate pair now hit `ffmpeg-export-side-data-mvs-cli-lacks-coordinate-vectors` on the same FFmpeg CLI decode path.

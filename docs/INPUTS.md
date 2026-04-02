# External Inputs Contract: MP4 Motion Vector Visualization

Status: Active
Last Updated: 2026-04-02

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
- Any required download, bootstrap, extraction, or preprocessing step should be
  scripted or documented in repo-local commands.

## Source Inputs

The workflow expects two MP4 source inputs for every comparison run.

### Public baseline pair

The baseline lane now has an exact shareable source-of-truth pair:

| Input | Retrieval URL | Provenance | Notes |
| --- | --- | --- | --- |
| `bbb_480p_30s` | `https://raw.githubusercontent.com/chthomos/video-media-samples/master/big-buck-bunny-480p-30sec.mp4` | `chthomos/video-media-samples` | Big Buck Bunny 30 second H.264/AAC MP4 sample at 480p |
| `bbb_1080p_30s` | `https://raw.githubusercontent.com/chthomos/video-media-samples/master/big-buck-bunny-1080p-30sec.mp4` | `chthomos/video-media-samples` | Big Buck Bunny 30 second H.264/AAC MP4 sample at 1080p |

Supporting provenance:
- source page: `https://github.com/chthomos/video-media-samples`
- license text: `https://raw.githubusercontent.com/chthomos/video-media-samples/master/LICENSE.md`
- license note: the repository is MIT-licensed; the bundled Big Buck Bunny footage is CC BY 3.0 per upstream `LICENSE.md`

Why this pair:
- both files are public and directly retrievable without auth
- both files are MP4/H.264/AAC and small enough for repeated baseline runs
- they keep content constant while changing encode characteristics, which is useful for the first comparison lane

### Private/user validation pair

Private inputs are not required to complete HEL-150.

When HEL-152 begins, user-provided MP4 files should be copied into the shared
cache under:

- raw private inputs: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/<run-id>/`
- prepared private metadata: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/prepared/<run-id>/`

The private lane should reuse the same manifest shape created here, replacing
public `source_url` fields with secure provenance notes.

Repo-local private manifest template:

- template config: `configs/input_sets/private-template.json`
- private staging wrapper: `scripts/prepare_private_inputs.sh`
- private validation wrapper: `scripts/run_private_validation.sh`

When the user MP4 pair becomes available, stage the manifest with:

```bash
scripts/run_private_validation.sh
```

What this private flow does:

1. reads `local_path` entries instead of public `source_url` downloads
2. fails early with `python3 scripts/validate_private_input_config.py --config ...` when the private config still points at placeholder or missing local files, and writes that blocker to `.symphony/progress/HEL-152.json`
3. bootstraps a reusable static `ffprobe`/`ffmpeg` toolchain under `/home/helionaut/srv/research-cache/18afd661ce11/toolchains/` if it is not already cached
4. copies the staged user MP4 files into `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/<run-id>/`
5. writes ffprobe sidecars into `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/prepared/<run-id>/probe/`
6. emits a manifest with the same downstream shape as the public lane, but with `source_url: null`
7. runs `python3 scripts/public_baseline.py run --manifest manifests/user-validation.json` against that staged private manifest

Override notes:

- `MP4_MV_PRIVATE_INPUT_CONFIG` can point to a non-default private config file
- `MP4_MV_PRIVATE_MANIFEST_OUT` can change the output manifest path
- `MP4_MV_PROGRESS_ARTIFACT` can redirect the machine-readable blocker/ready artifact when the wrapper is used outside the default issue workspace
- `scripts/prepare_private_inputs.sh` is still available when only the staging step is needed without immediately running the lane

## Prepared Artifacts

The downstream workflow should consume these prepared artifacts:

- normalized run manifest
  - generator: `scripts/prepare_public_inputs.sh`
  - output path: `manifests/public-baseline.json` for the first baseline run
  - purpose: records the two MP4 inputs, raw paths, SHA-256 digests, ffprobe summaries, and downstream output directories
- ffprobe sidecars
  - generator: `scripts/prepare_inputs.py`
  - output path: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/prepared/<run-id>/probe/<input-name>.ffprobe.json`
  - purpose: preserves full codec/container metadata per input
- extracted motion-vector data
  - generator: downstream extractor lane
  - output path: `reports/out/<run-id>/vectors/<input-name>.json`
  - purpose: per-frame vector data for rendering and comparison
- render artifacts
  - generator: downstream visualization lane
  - output path: `reports/out/<run-id>/renders/`
  - purpose: visual overlays or frame summaries per input
- comparison artifact
  - generator: downstream comparison lane
  - output path: `reports/out/<run-id>/comparison/`
  - purpose: side-by-side or aggregate comparison output

## Deterministic Paths

Repo-local control files:
- input catalog: `configs/input_sets/public-baseline.json`
- private input template: `configs/input_sets/private-template.json`
- manifest generator: `scripts/prepare_inputs.py`
- public baseline wrapper: `scripts/prepare_public_inputs.sh`
- private staging wrapper: `scripts/prepare_private_inputs.sh`
- private validation wrapper: `scripts/run_private_validation.sh`
- media-tools bootstrap: `scripts/bootstrap_media_tools.sh`
- generated manifest: `manifests/public-baseline.json`

Shared-cache raw and prepared paths:
- public raw inputs: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/raw/<run-id>/`
- public prepared metadata: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/prepared/<run-id>/`
- private raw inputs: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/raw/<run-id>/`
- private prepared metadata: `/home/helionaut/srv/research-cache/18afd661ce11/datasets/user/prepared/<run-id>/`
- heavy downstream artifacts: `/home/helionaut/srv/research-cache/18afd661ce11/artifacts/`

The repo keeps only scripts, configs, manifests, and lightweight docs. The
authoritative copies of reusable media files and ffprobe sidecars live under the
shared research cache root.

## Bootstrap And Acquisition

### One-command baseline preparation

Run this from the repo root:

```bash
scripts/prepare_public_inputs.sh
```

What it does:
1. downloads a static FFmpeg/ffprobe build into `/home/helionaut/srv/research-cache/18afd661ce11/toolchains/` if the helper cache is empty
2. downloads the two public MP4 inputs into `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/raw/public-baseline/` if they are not already cached
3. runs `ffprobe -show_format -show_streams` on each MP4
4. writes full ffprobe JSON sidecars into `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/prepared/public-baseline/probe/`
5. writes the normalized manifest to `manifests/public-baseline.json`

### Manual component commands

If a later lane needs to customize paths:

```bash
scripts/bootstrap_media_tools.sh
python3 scripts/prepare_inputs.py \
  --config configs/input_sets/public-baseline.json \
  --manifest-out manifests/public-baseline.json \
  --ffprobe-bin "$(scripts/bootstrap_media_tools.sh)"
```

## Real Gaps

- Public baseline pair: no longer missing.
  - Result: HEL-151 can start from `configs/input_sets/public-baseline.json` and `manifests/public-baseline.json` instead of rediscovering input sources.
- Private/user MP4 pair: still intentionally absent.
  - Why it is not a current blocker: HEL-152 is the first lane that should depend on those assets.
  - What is already unblocked: deterministic private raw/prepared paths and a reusable manifest shape are now defined.

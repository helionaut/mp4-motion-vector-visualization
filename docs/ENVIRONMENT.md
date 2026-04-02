# Environment Contract

Project: MP4 Motion Vector Visualization
Project mode: `research`
Default execution strategy: `docker`

## Why this file exists

This project must be reproducible across multiple Symphony issue workspaces and multiple future agents.

Issue workspaces are disposable. Reusable environment decisions, heavy downloads, toolchains, datasets, and build outputs must not live only inside a single `HEL-*` workspace.

## Chosen strategy

- Selected strategy: `docker`
- Why `docker` won:
  - FFmpeg and related media tooling are native system dependencies, so host bootstrap drift would be expensive and hard to audit.
  - The project is explicitly `research-heavy`, so a cache-mounted container baseline is a better long-term contract than host notes.
  - Future issues need one command surface they can reuse without rediscovering package installs or hidden mount paths.
- Why `host` was rejected:
  - there is no existing stable host bootstrap in this repo
  - repeating `apt`/system setup on disposable issue workspaces would violate the reproducibility goal
  - the project guardrails explicitly default to Docker for this class of task

The environment contract is now the repo-local Docker image plus `scripts/run_in_docker.sh`. Heavy retries should use that contract instead of ad hoc host setup.

## Image baseline

Committed baseline:

- `Dockerfile`
- base image: `debian:bookworm-slim`
- installed packages: `ffmpeg`, `python3`, `python3-venv`, `git`, `bash`, `ca-certificates`, `tini`
- runtime user: a non-root `worker` user created from the caller's UID/GID at build time

This is intentionally narrow. Optional plotting or notebook dependencies should be added only when a later issue proves they are required for the first render artifact.

## Shared cache contract

Canonical shared cache root:

- `/home/helionaut/srv/research-cache/18afd661ce11`

Stable subdirectories:

- downloads: `/home/helionaut/srv/research-cache/18afd661ce11/downloads`
- datasets: `/home/helionaut/srv/research-cache/18afd661ce11/datasets`
- toolchains: `/home/helionaut/srv/research-cache/18afd661ce11/toolchains`
- builds: `/home/helionaut/srv/research-cache/18afd661ce11/builds`
- artifacts: `/home/helionaut/srv/research-cache/18afd661ce11/artifacts`
- logs: `/home/helionaut/srv/research-cache/18afd661ce11/logs`
- docker state: `/home/helionaut/srv/research-cache/18afd661ce11/docker`

Wrapper behavior:

- `scripts/run_in_docker.sh` creates the full directory layout before every `build`, `run`, or `dry-run`.
- The repo checkout is mounted at `/workspace`.
- The shared cache root is mounted at `/cache-root`.
- Inside the container, these environment variables are always exported:
  - `MMV_CACHE_ROOT=/cache-root`
  - `MMV_DOWNLOADS_DIR=/cache-root/downloads`
  - `MMV_DATASETS_DIR=/cache-root/datasets`
  - `MMV_TOOLCHAINS_DIR=/cache-root/toolchains`
  - `MMV_BUILDS_DIR=/cache-root/builds`
  - `MMV_ARTIFACTS_DIR=/cache-root/artifacts`
  - `MMV_LOGS_DIR=/cache-root/logs`
  - `MMV_DOCKER_STATE_DIR=/cache-root/docker`

Output discipline:

- reusable downloads, datasets, build trees, and research artifacts go under the shared cache root
- disposable repo edits, docs, and orchestration scripts stay in the issue workspace checkout
- future agents may override the host cache root with `MMV_CACHE_ROOT`, but they should preserve the same subdirectory contract

## Entry wrapper contract

Primary entrypoint:

- `scripts/run_in_docker.sh doctor`
- `scripts/run_in_docker.sh dry-run`
- `scripts/run_in_docker.sh build`
- `scripts/run_in_docker.sh run -- <command>`
- `scripts/run_in_docker.sh ffmpeg-version`

Operational notes:

- `doctor` prints the resolved repo path, Docker binary, image name, and cache locations
- `dry-run` prints the exact `docker build` and `docker run` commands without requiring Docker to be installed
- `build` and `run` fail fast with an explicit error if Docker is unavailable
- `run` rebuilds the image before execution so future agents do not silently reuse a stale environment definition

## First environment target

HEL-149 establishes the smallest reusable container baseline that can:

- run FFmpeg and ffprobe against MP4 inputs
- write extracted vector data and rendered artifacts to mounted cache-backed paths
- give future agents one repo-local command surface instead of undocumented host steps

The first environment lane does not claim the extraction path is solved. It only locks the environment needed to pursue that path reproducibly.

## Validation and handoff proof

Static validation committed in this repo:

- `python3 scripts/validate_intake_docs.py`
- `python3 scripts/validate_environment_contract.py`

The environment validator proves:

- the Dockerfile exists with the expected baseline packages
- the wrapper is executable and exposes `doctor` plus `dry-run`
- the dry-run output includes the cache mount contract and Docker invocation shape
- the docs reference the same wrapper and cache contract that the validator checks

Live runtime proof on a Docker-capable machine:

```bash
scripts/run_in_docker.sh ffmpeg-version
scripts/run_in_docker.sh run ffprobe -version
```

These commands are the required starting point for future agents before any heavy extraction/build retry begins.

## Known blocker on the current machine

The current workspace host does not have a `docker` CLI available, so HEL-149 cannot honestly claim a locally executed container build/run proof from this machine alone.

What is still proven here:

- the Docker strategy is selected and documented
- the repo-local Dockerfile and wrapper are committed
- the cache layout is explicit and validated
- future agents have a single command surface to reuse without hidden setup

What still requires infrastructure:

- one Docker-capable host needs to run `scripts/run_in_docker.sh ffmpeg-version` and `scripts/run_in_docker.sh run ffprobe -version`
- once that succeeds, write the validation artifact and reuse the same wrapper for later experiment issues

## Extractor follow-up reuse contract

The next public extractor recovery slice must keep this environment contract fixed while changing only the extraction surface.

- Reuse the same Docker wrapper and cache root:
  - `scripts/run_in_docker.sh`
  - `/home/helionaut/srv/research-cache/18afd661ce11`
- Reuse prepared public inputs and manifest outputs instead of rebuilding them:
  - `scripts/prepare_public_inputs.sh`
  - `manifests/public-baseline.json`
  - shared-cache prepared inputs under `/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/`
- Validation for that slice must stay explicit:
  - rerun the prepared public baseline with one deterministic command surface
  - emit a machine-readable runtime progress artifact with counters/metrics
  - either publish non-empty vector artifacts plus refreshed render/comparison evidence or record the exact failure boundary for the alternate extractor surface
- If Docker is still unavailable on the executing machine, the handoff must say that the code/docs slice shipped but live container validation remains blocked by missing Docker-capable infrastructure

## Reuse rules

- Never leave the only copy of a useful baseline inside a disposable issue workspace.
- Commit repo-local wrappers, manifests, patches, lockfiles, and runbooks.
- If using `docker`, commit the Dockerfile and repo-local entry script; mount the shared cache root into the container.
- If using `host`, commit `scripts/bootstrap_host_deps.sh` before allowing repeated build retries.
- Every follow-up issue must say which environment baseline or cache paths it expects to reuse.

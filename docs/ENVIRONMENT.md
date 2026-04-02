# Environment Contract

Project: MP4 Motion Vector Visualization
Project mode: `research`
Default execution strategy: `docker`

## Why this file exists

This project must be reproducible across multiple Symphony issue workspaces and multiple future agents.

Issue workspaces are disposable. Reusable environment decisions, heavy downloads, toolchains, datasets, and build outputs must not live only inside a single `HEL-*` workspace.

## Decision rule

- Default to `docker` for research/native-build tasks when any of these are true:
  - the task compiles native code or depends on `apt`/system packages
  - the build or test run is expensive enough that repeated host bootstrap would waste time or tokens
  - the result must be reproducible across future agents or hosts
- Use `host` only when:
  - the stack is lightweight and already stable on the host
  - the host bootstrap can be captured in a small repo-local script
  - containerizing the task adds more complexity than reproducibility value
- The decision must be recorded before repeated retries begin.

## Current contract

- Strategy: `docker`
- Status: `draft until HEL-149 locks the first known-good baseline`
- Shared cache root: `/home/helionaut/srv/research-cache/18afd661ce11`
- Stable subdirectories:
  - downloads: `/home/helionaut/srv/research-cache/18afd661ce11/downloads`
  - datasets: `/home/helionaut/srv/research-cache/18afd661ce11/datasets`
  - toolchains: `/home/helionaut/srv/research-cache/18afd661ce11/toolchains`
  - builds: `/home/helionaut/srv/research-cache/18afd661ce11/builds`
  - artifacts: `/home/helionaut/srv/research-cache/18afd661ce11/artifacts`
  - logs: `/home/helionaut/srv/research-cache/18afd661ce11/logs`
  - docker state/volumes: `/home/helionaut/srv/research-cache/18afd661ce11/docker`

## First environment target

HEL-149 should produce the smallest reproducible container baseline that can:

- run FFmpeg/ffprobe against MP4 inputs
- write extracted vector data and rendered artifacts to mounted cache-backed paths
- expose one repo-local entry command future agents can reuse without host-specific guesswork

The first environment lane should not optimize performance or add optional tooling until the baseline extraction path is proven.

## Expected mounted paths

- repo workspace: disposable checkout for scripts and docs
- shared datasets/artifacts/logs: mounted from `/home/helionaut/srv/research-cache/18afd661ce11`
- output discipline: reusable downloads, datasets, and heavy build outputs must stay under the shared cache root

## Likely package surface

Record and justify the final list in HEL-149, but the baseline should assume:

- FFmpeg and ffprobe
- Python 3 for orchestration/reporting helpers
- optional image/video plotting dependencies only if the first render artifact requires them

## Reuse rules

- Never leave the only copy of a useful baseline inside a disposable issue workspace.
- Commit repo-local wrappers, manifests, patches, lockfiles, and runbooks.
- If using `docker`, commit the Dockerfile and repo-local entry script; mount the shared cache root into the container.
- If using `host`, commit `scripts/bootstrap_host_deps.sh` (or equivalent) before allowing repeated build retries.
- Every follow-up issue must say which environment baseline or cache paths it expects to reuse.

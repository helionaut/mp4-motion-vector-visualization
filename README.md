# mp4-motion-vector-visualization

Symphony-managed project: MP4 Motion Vector Visualization

## Current planning entry points

- [docs/PLAN.md](docs/PLAN.md): intake translation, execution order, and issue-pack exit signals
- [docs/RESEARCH.md](docs/RESEARCH.md): research contract, baseline hypothesis, and changed-variable discipline
- [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md): Docker-first reproducibility contract and shared cache paths
- [docs/INPUTS.md](docs/INPUTS.md): MP4 input contract and prepared artifact expectations

## Environment entry point

- `scripts/run_in_docker.sh doctor`: print the selected Docker/cache contract
- `scripts/run_in_docker.sh dry-run`: print the exact `docker build` and `docker run` commands the baseline uses
- `scripts/run_in_docker.sh ffmpeg-version`: prove the containerized FFmpeg baseline on a Docker-capable machine

## Public baseline entry point

- `manifests/public_known_good_baseline.json`: deterministic two-input public baseline manifest
- `python3 scripts/public_baseline.py plan --manifest manifests/public_known_good_baseline.json`: print the exact baseline plan and generation commands
- `scripts/run_in_docker.sh run -- python3 scripts/public_baseline.py run --manifest manifests/public_known_good_baseline.json`: execute the known-good baseline inside the documented Docker contract

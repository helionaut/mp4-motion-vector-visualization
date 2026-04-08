# mp4-motion-vector-visualization

Symphony-managed project: MP4 Motion Vector Visualization

## Current planning entry points

- [docs/PLAN.md](docs/PLAN.md): intake translation, execution order, and issue-pack exit signals
- [docs/RESEARCH.md](docs/RESEARCH.md): research contract, baseline hypothesis, and changed-variable discipline
- [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md): Docker-first reproducibility contract and shared cache paths
- [docs/INPUTS.md](docs/INPUTS.md): MP4 input contract and prepared artifact expectations
- [docs/BROWSER_MVP.md](docs/BROWSER_MVP.md): browser-first MVP scope, runtime assumptions, and honest platform boundary

## Environment entry point

- `scripts/run_in_docker.sh doctor`: print the selected Docker/cache contract
- `scripts/run_in_docker.sh dry-run`: print the exact `docker build` and `docker run` commands the baseline uses
- `scripts/run_in_docker.sh ffmpeg-version`: prove the containerized FFmpeg baseline on a Docker-capable machine

## Browser demo entry point

- `npm run serve`
- open `http://localhost:4173/browser-demo/`
- use the pair-upload fallback lane to load two MP4 files locally
- the overlay mode is currently `optical-flow-approximation`, not codec motion vectors
- after merge to `main`, GitHub Pages publishes the same static demo from `browser-demo/`

## Public baseline entry point

- `scripts/prepare_public_inputs.sh`: fetch the committed public MP4 pair and write `manifests/public-baseline.json`
- `scripts/bootstrap_host_libavcodec.sh --output build/host/libavcodec_mv_extractor`: build the HEL-156 host-side coordinate extractor when FFmpeg development packages are available on the machine
- `python3 scripts/public_baseline.py plan --manifest manifests/public-baseline.json`: print the exact extraction/render plan for the prepared public baseline
- `python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`: execute the public baseline against the prepared input manifest

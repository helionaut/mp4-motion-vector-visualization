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
- open `http://localhost:4173/`
- use the pair-upload fallback lane to load two MP4 files locally
- the overlay mode is currently `optical-flow-approximation`, not codec motion vectors
- GitHub Pages deploys the contents of `browser-demo/` as the site root for review
- live review deploy: `https://helionaut.github.io/mp4-motion-vector-visualization-review/`
- review Pages repo: `https://github.com/helionaut/mp4-motion-vector-visualization-review`

## Public baseline entry point

- `scripts/prepare_public_inputs.sh`: fetch the committed public MP4 pair and write `manifests/public-baseline.json`
- `scripts/bootstrap_host_libavcodec.sh --output build/host/libavcodec_mv_extractor`: build the HEL-156 host-side coordinate extractor when FFmpeg development packages are available on the machine
- `python3 scripts/public_baseline.py plan --manifest manifests/public-baseline.json`: print the exact extraction/render plan for the prepared public baseline
- `python3 scripts/public_baseline.py run --manifest manifests/public-baseline.json`: execute the public baseline against the prepared input manifest

## Dense codec-flow artifact

- `python3 scripts/render_dense_flow.py --vectors <vectors.json> --video <input.mp4> --output-dir <dir>`: render a dense optical-flow-style map from real codec motion vectors
- output includes:
  - `dense-flow-raw.{svg,png}`: the codec grid rendered without the source frame
  - `dense-flow-overlay.{svg,png}`: the same field over the decoded frame with configurable overlay alpha
  - `summary.json`: selected frame, magnitude scale, block-size coverage, and explicit limitations
- honest limitation: density is limited to the motion-vector grid the codec exposes, typically block-sized cells such as `8x8` and `16x16`, not per-pixel optical flow

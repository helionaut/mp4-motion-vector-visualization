# Browser MVP

## What this slice proves

HEL-158 adds a browser-first local demo that keeps the primary interaction on
the client machine:

- the user can open a local browser page
- upload a derived MP4 pair
- play both streams side by side
- toggle a motion overlay
- see an explicit mode label: `optical-flow-approximation`

This slice does **not** claim browser-side codec motion vectors. The browser
overlay is computed from decoded frames and presented honestly as an
approximation.

## Browser architecture choice

The app is a static browser surface under `browser-demo/` with no frontend
build dependency:

- `browser-demo/index.html`: product-facing UI
- `browser-demo/app.js`: file handling, synchronized playback, status updates,
  and overlay wiring
- `browser-demo/flow-worker.js`: worker entry point that keeps motion analysis
  off the main UI thread
- `browser-demo/lib/flow-core.js`: shared pure logic for split-state messaging
  and sparse optical-flow estimation

Architecture decisions:

- Use ordinary browser file inputs and `URL.createObjectURL()` for local media.
- Use two native `<video>` elements to keep playback credible and easy to
  inspect.
- Use hidden canvases to sample decoded frames at a reduced resolution.
- Send luminance planes to a worker for sparse block-matching, then draw the
  returned vectors on overlay canvases.

## Why the single-file split falls back

The UI includes a single-file Insta360 input so the user can see the intended
entry point, but the MVP stops at an explicit blocker instead of faking a split.

Exact blocker:

- the repo's proven extraction/splitting surfaces currently rely on host
  FFmpeg/libav tooling
- standard browser media APIs do not expose a truthful built-in way to demux or
  derive the required pair from one Insta360 source file
- shipping a pretend split here would overclaim what the browser actually did

The same screen therefore offers the working fallback lane: upload the already
derived MP4 pair.

## Runtime assumptions

Tested assumptions for the MVP:

- modern Chromium-class browser
- support for ES modules, Web Workers, and `requestVideoFrameCallback`
- local static serving, for example:

```bash
npm run serve
```

Open `http://localhost:4173/browser-demo/`.

## Performance limits for the first slice

This is a short-clip demo, not a production pipeline.

- recommended clip length: roughly 30 seconds or less
- recommended resolution: 1080p or below
- motion estimation runs on downscaled `160x90` frame samples
- analysis samples every 3 frame callbacks by default
- the overlay is sparse and qualitative; it is for visual credibility checks,
  not for measurement-grade motion analysis

## What remains after this MVP

- truthful client-side single-file Insta360 split, likely requiring a worker
  plus WASM/libav or another committed browser-demux path
- truthful browser-side `codec-motion-vectors` mode instead of the current
  `optical-flow-approximation`
- validation on a larger matrix of browsers and longer clips
- tighter UX around ingest progress, cancellation, and generated artifact reuse

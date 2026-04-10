import {
  FLOW_MODE,
  computeLumaPlane,
  describeSplitAttempt,
  estimateMotionVectors,
  formatFileMeta,
  getDenseFlowSampling,
  getFrameStepSeconds,
  getContainedVideoRect,
  getMaximumMotionMagnitude,
  getMotionFieldCell,
  getMotionFieldColor,
  projectMotionVector,
  stepPlaybackTime
} from "./lib/flow-core.js";

const state = {
  mode: FLOW_MODE,
  overlayVisible: true,
  syncEnabled: true,
  sampleStride: 1,
  statusEntries: [],
  activeViewer: "a"
};

const elements = {
  sourceFile: document.querySelector("#source-file"),
  attemptSplit: document.querySelector("#attempt-split"),
  splitStatus: document.querySelector("#split-status"),
  pairA: document.querySelector("#pair-a"),
  pairB: document.querySelector("#pair-b"),
  loadPair: document.querySelector("#load-pair"),
  mode: document.querySelector("#visualization-mode"),
  playPause: document.querySelector("#play-pause"),
  stepBackward: document.querySelector("#step-backward"),
  stepForward: document.querySelector("#step-forward"),
  playbackDetail: document.querySelector("#playback-detail"),
  overlayToggle: document.querySelector("#overlay-toggle"),
  syncToggle: document.querySelector("#sync-toggle"),
  sampleStride: document.querySelector("#sample-stride"),
  statusBadge: document.querySelector("#status-badge"),
  statusDetail: document.querySelector("#status-detail"),
  statusLog: document.querySelector("#status-log"),
  videoA: document.querySelector("#video-a"),
  videoB: document.querySelector("#video-b"),
  overlayA: document.querySelector("#overlay-a"),
  overlayB: document.querySelector("#overlay-b"),
  metaA: document.querySelector("#meta-a"),
  metaB: document.querySelector("#meta-b")
};

elements.mode.textContent = state.mode;

function pushStatus(badge, detail) {
  state.statusEntries.unshift(`${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - ${detail}`);
  state.statusEntries = state.statusEntries.slice(0, 8);
  elements.statusBadge.textContent = badge;
  elements.statusDetail.textContent = detail;
  elements.statusLog.innerHTML = "";
  for (const entry of state.statusEntries) {
    const item = document.createElement("li");
    item.textContent = entry;
    elements.statusLog.appendChild(item);
  }
}

function getLoadedVideos() {
  return [elements.videoA, elements.videoB].filter((video) => video.currentSrc);
}

function getControlTargets() {
  if (state.syncEnabled) {
    return getLoadedVideos();
  }

  const activeVideo = state.activeViewer === "b" ? elements.videoB : elements.videoA;
  return activeVideo.currentSrc ? [activeVideo] : [];
}

function describePlaybackTarget() {
  return state.syncEnabled ? "both streams" : `stream ${state.activeViewer.toUpperCase()}`;
}

function setPlaybackButtonLabel() {
  const targets = getLoadedVideos();
  const shouldPause = targets.some((video) => !video.paused && !video.ended);
  elements.playPause.textContent = shouldPause ? "Pause" : "Play both";
}

function updatePlaybackDetail() {
  const analyzersForDetail = state.syncEnabled
    ? Object.values(analyzers).filter((analyzer) => analyzer.video.currentSrc)
    : [analyzers[state.activeViewer]].filter((analyzer) => analyzer.video.currentSrc);
  const measuredSteps = analyzersForDetail
    .map((analyzer) => analyzer.estimatedFrameStepSeconds)
    .filter((value) => Number.isFinite(value));
  const averageStep =
    measuredSteps.length > 0
      ? measuredSteps.reduce((sum, value) => sum + value, 0) / measuredSteps.length
      : getFrameStepSeconds();
  const roundedMs = Math.round(averageStep * 1000 * 10) / 10;
  const targetLabel = state.syncEnabled ? "both streams" : `stream ${state.activeViewer.toUpperCase()}`;
  elements.playbackDetail.textContent = `Frame step for ${targetLabel}: about ${roundedMs} ms.`;
}

async function seekVideo(video, nextTime) {
  if (!video.currentSrc) {
    return;
  }

  const clampedTime = Math.max(0, nextTime);
  if (Math.abs(video.currentTime - clampedTime) < 0.0005) {
    return;
  }

  await new Promise((resolve) => {
    let resolved = false;
    const finish = () => {
      if (resolved) {
        return;
      }
      resolved = true;
      resolve();
    };
    const timeoutId = window.setTimeout(finish, 150);
    video.addEventListener(
      "seeked",
      () => {
        window.clearTimeout(timeoutId);
        finish();
      },
      { once: true }
    );
    video.currentTime = clampedTime;
  });
}

async function stepTargets(frameDelta) {
  const targets = getControlTargets();
  if (targets.length === 0) {
    pushStatus("Missing files", "Load one or both streams before stepping frame-by-frame.");
    return;
  }

  for (const video of targets) {
    video.pause();
  }

  await Promise.all(
    targets.map((video) => {
      const analyzer = video === elements.videoB ? analyzers.b : analyzers.a;
      const frameStepSeconds = getFrameStepSeconds(analyzer.estimatedFrameStepSeconds);
      return seekVideo(
        video,
        stepPlaybackTime({
          currentTime: video.currentTime,
          duration: video.duration,
          frameStepSeconds,
          frameDelta
        })
      );
    })
  );

  setPlaybackButtonLabel();
  updatePlaybackDetail();
  pushStatus(
    "Frame step",
    `${frameDelta > 0 ? "Advanced" : "Moved back"} one frame on ${describePlaybackTarget()}.`
  );
}

async function togglePlayback() {
  const targets = getControlTargets();
  if (targets.length === 0) {
    pushStatus("Missing files", "Load one or both streams before using playback controls.");
    return;
  }

  const shouldPause = targets.some((video) => !video.paused && !video.ended);
  if (shouldPause) {
    for (const video of targets) {
      video.pause();
    }
    setPlaybackButtonLabel();
    pushStatus("Paused", `Paused ${describePlaybackTarget()}.`);
    return;
  }

  if (state.syncEnabled && targets.length > 1) {
    const referenceTime = targets[0].currentTime;
    for (const video of targets.slice(1)) {
      video.currentTime = referenceTime;
    }
  }

  await Promise.all(
    targets.map((video) =>
      video.play().catch(() => {
        pushStatus("Ready", "Playback is loaded. Press play in the browser if autoplay is blocked.");
      })
    )
  );
  setPlaybackButtonLabel();
  updatePlaybackDetail();
}

function updateViewerMeta(metaElement, analyzer) {
  const base = formatFileMeta(analyzer.file, analyzer.metadata);
  if (!analyzer.file) {
    metaElement.textContent = base;
    return;
  }

  metaElement.textContent = `${base} • analysis ${analyzer.analysisWidth}x${analyzer.analysisHeight} • grid ${analyzer.gridStep}px`;
}

class VideoAnalyzer {
  constructor({ name, video, overlay }) {
    this.name = name;
    this.video = video;
    this.overlay = overlay;
    this.hiddenCanvas = document.createElement("canvas");
    this.hiddenContext = this.hiddenCanvas.getContext("2d", { willReadFrequently: true });
    this.overlayContext = overlay.getContext("2d");
    this.previousPlane = null;
    this.sampleCounter = 0;
    this.analysisWidth = 480;
    this.analysisHeight = 270;
    this.gridStep = 6;
    this.sampleSize = 6;
    this.searchRadius = 4;
    this.minimumConfidence = 14;
    this.frameCallbackBound = this.onFrame.bind(this);
    this.latestVectors = [];
    this.metadata = {};
    this.currentFrameToken = 0;
    this.lastRenderedFrameToken = 0;
    this.lastMediaTime = null;
    this.lastPresentedFrames = null;
    this.estimatedFrameStepSeconds = null;

    video.addEventListener("loadedmetadata", () => {
      this.metadata = {
        width: video.videoWidth,
        height: video.videoHeight,
        duration: video.duration
      };
      const sampling = getDenseFlowSampling({
        videoWidth: video.videoWidth,
        videoHeight: video.videoHeight
      });
      this.analysisWidth = sampling.analysisWidth;
      this.analysisHeight = sampling.analysisHeight;
      this.gridStep = sampling.gridStep;
      this.sampleSize = sampling.sampleSize;
      this.searchRadius = sampling.searchRadius;
      this.minimumConfidence = sampling.minimumConfidence;
      this.resizeCanvases();
      this.renderOverlay();
      updateViewerMeta(this.name === "a" ? elements.metaA : elements.metaB, this);
      updatePlaybackDetail();
    });
    video.addEventListener("play", () => this.schedule());
    video.addEventListener("seeked", () => this.reset());
    video.addEventListener("emptied", () => this.reset(true));
    video.addEventListener("play", () => setPlaybackButtonLabel());
    video.addEventListener("pause", () => setPlaybackButtonLabel());
    video.addEventListener("ended", () => setPlaybackButtonLabel());
    video.addEventListener("pointerdown", () => {
      state.activeViewer = this.name;
      updatePlaybackDetail();
    });
    window.addEventListener("resize", () => this.resizeCanvases());
  }

  attachFile(file) {
    this.file = file;
    this.reset(true);
  }

  reset(clear = false) {
    this.previousPlane = null;
    this.latestVectors = [];
    this.sampleCounter = 0;
    this.currentFrameToken = 0;
    this.lastRenderedFrameToken = 0;
    this.lastMediaTime = null;
    this.lastPresentedFrames = null;
    this.estimatedFrameStepSeconds = null;
    if (clear) {
      this.overlayContext.clearRect(0, 0, this.overlay.width, this.overlay.height);
    }
  }

  resizeCanvases() {
    const bounds = this.video.getBoundingClientRect();
    this.overlay.width = Math.max(1, Math.round(bounds.width));
    this.overlay.height = Math.max(1, Math.round(bounds.height));
    this.hiddenCanvas.width = this.analysisWidth;
    this.hiddenCanvas.height = this.analysisHeight;
    this.renderOverlay();
  }

  schedule() {
    if (!("requestVideoFrameCallback" in HTMLVideoElement.prototype)) {
      pushStatus(
        "Browser limit",
        "This browser does not support requestVideoFrameCallback; motion analysis is unavailable here."
      );
      return;
    }
    this.video.requestVideoFrameCallback(this.frameCallbackBound);
  }

  onFrame(_now, metadata = {}) {
    if (!this.video.paused && !this.video.ended) {
      if (
        Number.isFinite(metadata.mediaTime) &&
        Number.isFinite(metadata.presentedFrames) &&
        Number.isFinite(this.lastMediaTime) &&
        Number.isFinite(this.lastPresentedFrames)
      ) {
        const frameDelta = metadata.presentedFrames - this.lastPresentedFrames;
        const timeDelta = metadata.mediaTime - this.lastMediaTime;
        if (frameDelta > 0 && timeDelta > 0) {
          const nextEstimate = timeDelta / frameDelta;
          this.estimatedFrameStepSeconds = Number.isFinite(this.estimatedFrameStepSeconds)
            ? this.estimatedFrameStepSeconds * 0.7 + nextEstimate * 0.3
            : nextEstimate;
        }
      }
      this.lastMediaTime = Number.isFinite(metadata.mediaTime) ? metadata.mediaTime : this.lastMediaTime;
      this.lastPresentedFrames = Number.isFinite(metadata.presentedFrames)
        ? metadata.presentedFrames
        : this.lastPresentedFrames;
      this.currentFrameToken = Number.isFinite(metadata.presentedFrames)
        ? metadata.presentedFrames
        : this.currentFrameToken + 1;
      this.sampleCounter += 1;
      if (this.sampleCounter % state.sampleStride === 0) {
        this.captureFrame(this.currentFrameToken);
      }
      this.renderOverlay();
      updatePlaybackDetail();
      this.video.requestVideoFrameCallback(this.frameCallbackBound);
    }
  }

  captureFrame(frameToken) {
    if (this.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }

    this.hiddenContext.drawImage(this.video, 0, 0, this.analysisWidth, this.analysisHeight);
    const imageData = this.hiddenContext.getImageData(0, 0, this.analysisWidth, this.analysisHeight);
    const currentPlane = computeLumaPlane(imageData.data, this.analysisWidth, this.analysisHeight);

    if (!this.previousPlane) {
      this.previousPlane = currentPlane;
      return;
    }

    const previousPlane = this.previousPlane;
    this.previousPlane = currentPlane;
    this.latestVectors = estimateMotionVectors({
      previousFrame: previousPlane,
      currentFrame: currentPlane,
      width: this.analysisWidth,
      height: this.analysisHeight,
      gridStep: this.gridStep,
      sampleSize: this.sampleSize,
      searchRadius: this.searchRadius,
      minimumConfidence: this.minimumConfidence
    });
    this.lastRenderedFrameToken = frameToken;
  }

  renderOverlay() {
    this.overlayContext.clearRect(0, 0, this.overlay.width, this.overlay.height);
    if (!state.overlayVisible) {
      return;
    }

    const displayRect = getContainedVideoRect({
      containerWidth: this.overlay.width,
      containerHeight: this.overlay.height,
      videoWidth: this.metadata.width,
      videoHeight: this.metadata.height
    });
    const vectors = this.lastRenderedFrameToken === this.currentFrameToken ? this.latestVectors : [];
    const maximumMagnitude = getMaximumMotionMagnitude(vectors);

    this.overlayContext.save();
    this.overlayContext.beginPath();
    this.overlayContext.rect(displayRect.x, displayRect.y, displayRect.width, displayRect.height);
    this.overlayContext.clip();
    this.overlayContext.fillStyle = "rgba(4, 10, 18, 0.2)";
    this.overlayContext.fillRect(displayRect.x, displayRect.y, displayRect.width, displayRect.height);
    this.overlayContext.lineWidth = 1;

    for (const vector of vectors) {
      const cell = getMotionFieldCell({
        vector,
        analysisWidth: this.analysisWidth,
        analysisHeight: this.analysisHeight,
        displayRect,
        gridStep: this.gridStep
      });
      const fill = getMotionFieldColor(vector, maximumMagnitude);
      const { fromX, fromY, toX, toY } = projectMotionVector({
        vector,
        analysisWidth: this.analysisWidth,
        analysisHeight: this.analysisHeight,
        displayRect,
        vectorScale: 1.25
      });
      const magnitudeRatio = Math.min(
        1,
        Math.hypot(vector.dx, vector.dy) / Math.max(1, maximumMagnitude)
      );
      const lineAlpha = Math.min(0.9, 0.35 + magnitudeRatio * 0.45);

      this.overlayContext.fillStyle = fill;
      this.overlayContext.fillRect(cell.x, cell.y, cell.width, cell.height);

      this.overlayContext.strokeStyle = `rgba(245, 248, 255, ${lineAlpha.toFixed(2)})`;
      this.overlayContext.beginPath();
      this.overlayContext.moveTo(fromX, fromY);
      this.overlayContext.lineTo(toX, toY);
      this.overlayContext.stroke();

      this.overlayContext.fillStyle = "rgba(245, 248, 255, 0.55)";
      this.overlayContext.beginPath();
      this.overlayContext.arc(fromX, fromY, 1.4, 0, Math.PI * 2);
      this.overlayContext.fill();
    }

    this.overlayContext.restore();
  }
}

const analyzers = {
  a: new VideoAnalyzer({ name: "a", video: elements.videoA, overlay: elements.overlayA }),
  b: new VideoAnalyzer({ name: "b", video: elements.videoB, overlay: elements.overlayB })
};

function revokeObjectUrl(video) {
  if (video.dataset.objectUrl) {
    URL.revokeObjectURL(video.dataset.objectUrl);
    delete video.dataset.objectUrl;
  }
}

async function loadVideoFile(video, analyzer, file, metaElement) {
  revokeObjectUrl(video);
  analyzer.attachFile(file);
  const objectUrl = URL.createObjectURL(file);
  video.src = objectUrl;
  video.dataset.objectUrl = objectUrl;
  await video.play().catch(() => {
    pushStatus("Ready", `${file.name} loaded. Press play if autoplay is blocked.`);
  });
  updateViewerMeta(metaElement, analyzer);
  setPlaybackButtonLabel();
  updatePlaybackDetail();
}

async function refreshMetadata() {
  updateViewerMeta(elements.metaA, analyzers.a);
  updateViewerMeta(elements.metaB, analyzers.b);
}

async function loadPair() {
  const fileA = elements.pairA.files?.[0];
  const fileB = elements.pairB.files?.[0];

  if (!fileA || !fileB) {
    pushStatus("Missing files", "Choose both derived MP4 files before loading the pair.");
    return;
  }

  pushStatus("Loading", "Loading the uploaded pair into the browser players.");
  await Promise.all([
    loadVideoFile(elements.videoA, analyzers.a, fileA, elements.metaA),
    loadVideoFile(elements.videoB, analyzers.b, fileB, elements.metaB)
  ]);
  await refreshMetadata();
  pushStatus(
    "Analyzing",
    "Pair loaded. The overlay shows optical-flow approximation from decoded browser frames, not codec motion vectors."
  );
}

function syncPlayback(source, target) {
  if (!state.syncEnabled || !source.duration || !target.duration) {
    return;
  }

  const drift = Math.abs(source.currentTime - target.currentTime);
  if (drift > 0.08) {
    target.currentTime = source.currentTime;
  }
  if (source.paused && !target.paused) {
    target.pause();
  }
}

elements.videoA.addEventListener("timeupdate", () => syncPlayback(elements.videoA, elements.videoB));
elements.videoB.addEventListener("timeupdate", () => syncPlayback(elements.videoB, elements.videoA));
elements.videoA.addEventListener("timeupdate", () => updatePlaybackDetail());
elements.videoB.addEventListener("timeupdate", () => updatePlaybackDetail());
elements.videoA.addEventListener("play", () => {
  state.activeViewer = "a";
  if (state.syncEnabled && elements.videoB.src && elements.videoB.paused) {
    elements.videoB.play().catch(() => {});
  }
});
elements.videoB.addEventListener("play", () => {
  state.activeViewer = "b";
  if (state.syncEnabled && elements.videoA.src && elements.videoA.paused) {
    elements.videoA.play().catch(() => {});
  }
});

elements.attemptSplit.addEventListener("click", () => {
  const result = describeSplitAttempt(elements.sourceFile.files?.[0]);
  elements.splitStatus.textContent = `${result.detail} ${result.blocker}`;
  pushStatus("Blocked", `${result.detail} ${result.blocker}`);
});

elements.loadPair.addEventListener("click", () => {
  loadPair().catch((error) => {
    pushStatus("Error", `Could not load the uploaded pair: ${error.message}`);
  });
});

elements.playPause.addEventListener("click", () => {
  togglePlayback().catch((error) => {
    pushStatus("Error", `Could not change playback state: ${error.message}`);
  });
});
elements.stepBackward.addEventListener("click", () => {
  stepTargets(-1).catch((error) => {
    pushStatus("Error", `Could not move to the previous frame: ${error.message}`);
  });
});
elements.stepForward.addEventListener("click", () => {
  stepTargets(1).catch((error) => {
    pushStatus("Error", `Could not move to the next frame: ${error.message}`);
  });
});

elements.overlayToggle.addEventListener("change", () => {
  state.overlayVisible = elements.overlayToggle.checked;
  analyzers.a.renderOverlay();
  analyzers.b.renderOverlay();
});

elements.syncToggle.addEventListener("change", () => {
  state.syncEnabled = elements.syncToggle.checked;
  updatePlaybackDetail();
});

elements.sampleStride.value = String(state.sampleStride);

elements.sampleStride.addEventListener("input", () => {
  state.sampleStride = Number(elements.sampleStride.value);
  pushStatus("Updated", `Sampling every ${state.sampleStride} video frame callbacks.`);
});

pushStatus(
  "Idle",
  "Waiting for media. For this MVP, use the pair-upload fallback and treat the overlay as optical-flow approximation."
);
setPlaybackButtonLabel();
updatePlaybackDetail();

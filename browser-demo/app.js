import {
  DEFAULT_FRAME_RATE,
  DENSE_FLOW_ANALYSIS,
  FLOW_MODE,
  computeLumaPlane,
  describeSplitAttempt,
  estimateMotionVectors,
  formatFileMeta,
  getFrameStepDeltaSeconds,
  getContainedVideoRect,
  getMaximumMotionMagnitude,
  getMotionFieldCell,
  getMotionFieldColor,
  getSteppedTime,
  projectMotionVector
} from "./lib/flow-core.js";

const state = {
  mode: FLOW_MODE,
  overlayVisible: true,
  syncEnabled: true,
  sampleStride: 1,
  statusEntries: [],
  frameRequestId: 0
};

const elements = {
  sourceFile: document.querySelector("#source-file"),
  attemptSplit: document.querySelector("#attempt-split"),
  splitStatus: document.querySelector("#split-status"),
  pairA: document.querySelector("#pair-a"),
  pairB: document.querySelector("#pair-b"),
  loadPair: document.querySelector("#load-pair"),
  mode: document.querySelector("#visualization-mode"),
  overlayToggle: document.querySelector("#overlay-toggle"),
  syncToggle: document.querySelector("#sync-toggle"),
  sampleStride: document.querySelector("#sample-stride"),
  frameBack: document.querySelector("#frame-back"),
  playPause: document.querySelector("#play-pause"),
  frameForward: document.querySelector("#frame-forward"),
  vectorDetail: document.querySelector("#vector-detail"),
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
elements.vectorDetail.textContent = `Maximum (${DENSE_FLOW_ANALYSIS.gridStep}px grid)`;

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
    this.analysisWidth = DENSE_FLOW_ANALYSIS.analysisWidth;
    this.analysisHeight = DENSE_FLOW_ANALYSIS.analysisHeight;
    this.gridStep = DENSE_FLOW_ANALYSIS.gridStep;
    this.sampleSize = DENSE_FLOW_ANALYSIS.sampleSize;
    this.searchRadius = DENSE_FLOW_ANALYSIS.searchRadius;
    this.minimumConfidence = DENSE_FLOW_ANALYSIS.minimumConfidence;
    this.vectorScale = DENSE_FLOW_ANALYSIS.vectorScale;
    this.frameCallbackBound = this.onFrame.bind(this);
    this.latestVectors = [];
    this.metadata = {};
    this.currentFrameToken = 0;
    this.lastRenderedFrameToken = 0;
    this.pendingFrameStep = false;
    this.lastFrameMetadata = null;

    video.addEventListener("loadedmetadata", () => {
      this.metadata = {
        width: video.videoWidth,
        height: video.videoHeight,
        duration: video.duration,
        frameRate: DEFAULT_FRAME_RATE
      };
      this.resizeCanvases();
      this.renderOverlay();
    });
    video.addEventListener("play", () => this.schedule());
    video.addEventListener("seeked", () => this.handleSeeked());
    video.addEventListener("emptied", () => this.reset(true));
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
    this.pendingFrameStep = false;
    this.lastFrameMetadata = null;
    if (clear) {
      this.overlayContext.clearRect(0, 0, this.overlay.width, this.overlay.height);
    }
  }

  handleSeeked() {
    if (!this.pendingFrameStep) {
      this.reset();
      this.captureFrame(this.currentFrameToken);
      this.renderOverlay();
      return;
    }

    this.pendingFrameStep = false;
    const nextFrameToken = this.currentFrameToken + 1;
    this.currentFrameToken = nextFrameToken;
    this.captureFrame(nextFrameToken);
    this.renderOverlay();
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
      this.updateObservedFrameRate(metadata);
      this.currentFrameToken = Number.isFinite(metadata.presentedFrames)
        ? metadata.presentedFrames
        : this.currentFrameToken + 1;
      this.sampleCounter += 1;
      if (this.sampleCounter % state.sampleStride === 0) {
        this.captureFrame(this.currentFrameToken);
      }
      this.renderOverlay();
      this.lastFrameMetadata = metadata;
      this.video.requestVideoFrameCallback(this.frameCallbackBound);
    }
  }

  updateObservedFrameRate(metadata = {}) {
    if (!Number.isFinite(metadata.presentedFrames) || !Number.isFinite(metadata.mediaTime) || metadata.mediaTime <= 0) {
      return;
    }

    if (
      this.lastFrameMetadata &&
      Number.isFinite(this.lastFrameMetadata.presentedFrames) &&
      Number.isFinite(this.lastFrameMetadata.mediaTime)
    ) {
      const frameDelta = metadata.presentedFrames - this.lastFrameMetadata.presentedFrames;
      const timeDelta = metadata.mediaTime - this.lastFrameMetadata.mediaTime;
      if (frameDelta > 0 && timeDelta > 0) {
        this.metadata.frameRate = frameDelta / timeDelta;
        return;
      }
    }

    this.metadata.frameRate = metadata.presentedFrames / metadata.mediaTime;
  }

  captureCurrentPlane() {
    if (this.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return null;
    }

    this.hiddenContext.drawImage(this.video, 0, 0, this.analysisWidth, this.analysisHeight);
    const imageData = this.hiddenContext.getImageData(0, 0, this.analysisWidth, this.analysisHeight);
    return computeLumaPlane(imageData.data, this.analysisWidth, this.analysisHeight);
  }

  prepareForFrameStep() {
    const currentPlane = this.captureCurrentPlane();
    if (currentPlane) {
      this.previousPlane = currentPlane;
    }
    this.pendingFrameStep = true;
  }

  captureFrame(frameToken) {
    if (this.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }

    const currentPlane = this.captureCurrentPlane();
    if (!currentPlane) {
      return;
    }

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
        vectorScale: this.vectorScale
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

function getLoadedStreams() {
  return [
    { key: "a", video: elements.videoA, analyzer: analyzers.a },
    { key: "b", video: elements.videoB, analyzer: analyzers.b }
  ].filter(({ video }) => Boolean(video.src));
}

function syncPlaybackButton() {
  const loadedStreams = getLoadedStreams();
  const shouldPlay = loadedStreams.some(({ video }) => video.paused);
  elements.playPause.textContent = shouldPlay ? "Play pair" : "Pause pair";
}

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
  metaElement.textContent = formatFileMeta(file, analyzer.metadata);
}

async function refreshMetadata() {
  elements.metaA.textContent = formatFileMeta(analyzers.a.file, analyzers.a.metadata);
  elements.metaB.textContent = formatFileMeta(analyzers.b.file, analyzers.b.metadata);
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
    `Pair loaded. The overlay shows optical-flow approximation from decoded browser frames with a ${DENSE_FLOW_ANALYSIS.gridStep}px grid, not codec motion vectors.`
  );
  syncPlaybackButton();
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
elements.videoA.addEventListener("play", () => {
  if (state.syncEnabled && elements.videoB.src && elements.videoB.paused) {
    elements.videoB.play().catch(() => {});
  }
  syncPlaybackButton();
});
elements.videoB.addEventListener("play", () => {
  if (state.syncEnabled && elements.videoA.src && elements.videoA.paused) {
    elements.videoA.play().catch(() => {});
  }
  syncPlaybackButton();
});
elements.videoA.addEventListener("pause", () => syncPlaybackButton());
elements.videoB.addEventListener("pause", () => syncPlaybackButton());

async function togglePlayback() {
  const loadedStreams = getLoadedStreams();
  if (!loadedStreams.length) {
    pushStatus("Idle", "Load a pair before using the paired playback controls.");
    return;
  }

  const shouldPlay = loadedStreams.some(({ video }) => video.paused);
  if (shouldPlay) {
    await Promise.all(loadedStreams.map(({ video }) => video.play().catch(() => {})));
    pushStatus("Playing", "Paired playback started.");
  } else {
    for (const { video } of loadedStreams) {
      video.pause();
    }
    pushStatus("Paused", "Paired playback paused.");
  }
  syncPlaybackButton();
}

async function stepPlayback(direction) {
  const loadedStreams = getLoadedStreams();
  if (!loadedStreams.length) {
    pushStatus("Idle", "Load a pair before stepping frame by frame.");
    return;
  }

  for (const { video, analyzer } of loadedStreams) {
    video.pause();
    analyzer.prepareForFrameStep();
  }

  await Promise.all(
    loadedStreams.map(async ({ video, analyzer }) => {
      const targetTime = getSteppedTime({
        currentTime: video.currentTime,
        duration: video.duration,
        direction,
        frameRate: analyzer.metadata.frameRate
      });
      if (Math.abs(targetTime - video.currentTime) < getFrameStepDeltaSeconds(analyzer.metadata.frameRate) / 4) {
        analyzer.pendingFrameStep = false;
        const nextFrameToken = analyzer.currentFrameToken + 1;
        analyzer.currentFrameToken = nextFrameToken;
        analyzer.captureFrame(nextFrameToken);
        analyzer.renderOverlay();
        return;
      }

      const seeked = new Promise((resolve) => {
        video.addEventListener("seeked", resolve, { once: true });
      });
      video.currentTime = targetTime;
      await seeked;
    })
  );

  pushStatus(
    "Stepped",
    `Moved ${direction < 0 ? "back" : "forward"} by one frame using ${loadedStreams.length} loaded stream${loadedStreams.length === 1 ? "" : "s"}.`
  );
  syncPlaybackButton();
}

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

elements.overlayToggle.addEventListener("change", () => {
  state.overlayVisible = elements.overlayToggle.checked;
  analyzers.a.renderOverlay();
  analyzers.b.renderOverlay();
});

elements.syncToggle.addEventListener("change", () => {
  state.syncEnabled = elements.syncToggle.checked;
});

elements.sampleStride.value = String(state.sampleStride);

elements.sampleStride.addEventListener("input", () => {
  state.sampleStride = Number(elements.sampleStride.value);
  pushStatus("Updated", `Sampling every ${state.sampleStride} video frame callbacks.`);
});

elements.playPause.addEventListener("click", () => {
  togglePlayback().catch((error) => {
    pushStatus("Error", `Could not toggle playback: ${error.message}`);
  });
});

elements.frameBack.addEventListener("click", () => {
  stepPlayback(-1).catch((error) => {
    pushStatus("Error", `Could not step backward: ${error.message}`);
  });
});

elements.frameForward.addEventListener("click", () => {
  stepPlayback(1).catch((error) => {
    pushStatus("Error", `Could not step forward: ${error.message}`);
  });
});

syncPlaybackButton();

pushStatus(
  "Idle",
  "Waiting for media. For this MVP, use the pair-upload fallback and treat the overlay as optical-flow approximation."
);

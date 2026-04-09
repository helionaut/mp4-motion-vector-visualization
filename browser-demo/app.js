import {
  FLOW_MODE,
  computeLumaPlane,
  describeSplitAttempt,
  estimateMotionVectors,
  formatFileMeta,
  getContainedVideoRect,
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
    this.analysisWidth = 160;
    this.analysisHeight = 90;
    this.frameCallbackBound = this.onFrame.bind(this);
    this.latestVectors = [];
    this.metadata = {};
    this.currentFrameToken = 0;
    this.lastRenderedFrameToken = 0;

    video.addEventListener("loadedmetadata", () => {
      this.metadata = {
        width: video.videoWidth,
        height: video.videoHeight,
        duration: video.duration
      };
      this.resizeCanvases();
      this.renderOverlay();
    });
    video.addEventListener("play", () => this.schedule());
    video.addEventListener("seeked", () => this.reset());
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
      this.currentFrameToken = Number.isFinite(metadata.presentedFrames)
        ? metadata.presentedFrames
        : this.currentFrameToken + 1;
      this.sampleCounter += 1;
      if (this.sampleCounter % state.sampleStride === 0) {
        this.captureFrame(this.currentFrameToken);
      }
      this.renderOverlay();
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
      gridStep: 16,
      sampleSize: 10,
      searchRadius: 4,
      minimumConfidence: 22
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

    this.overlayContext.save();
    this.overlayContext.beginPath();
    this.overlayContext.rect(displayRect.x, displayRect.y, displayRect.width, displayRect.height);
    this.overlayContext.clip();
    this.overlayContext.strokeStyle = "#ffd166";
    this.overlayContext.fillStyle = "rgba(255, 209, 102, 0.28)";
    this.overlayContext.lineWidth = 1.4;

    for (const vector of vectors) {
      const { fromX, fromY, toX, toY } = projectMotionVector({
        vector,
        analysisWidth: this.analysisWidth,
        analysisHeight: this.analysisHeight,
        displayRect
      });

      this.overlayContext.beginPath();
      this.overlayContext.moveTo(fromX, fromY);
      this.overlayContext.lineTo(toX, toY);
      this.overlayContext.stroke();

      this.overlayContext.beginPath();
      this.overlayContext.arc(fromX, fromY, 1.6, 0, Math.PI * 2);
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
elements.videoA.addEventListener("play", () => {
  if (state.syncEnabled && elements.videoB.src && elements.videoB.paused) {
    elements.videoB.play().catch(() => {});
  }
});
elements.videoB.addEventListener("play", () => {
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

pushStatus(
  "Idle",
  "Waiting for media. For this MVP, use the pair-upload fallback and treat the overlay as optical-flow approximation."
);

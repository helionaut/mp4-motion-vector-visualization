export const FLOW_MODE = "optical-flow-approximation";
export const DEFAULT_FRAME_RATE = 30;
export const DENSE_FLOW_ANALYSIS = Object.freeze({
  analysisWidth: 320,
  analysisHeight: 180,
  gridStep: 8,
  sampleSize: 6,
  searchRadius: 4,
  minimumConfidence: 14,
  vectorScale: 1.1
});

export function describeSplitAttempt(file) {
  if (!file) {
    return {
      ok: false,
      status: "blocked",
      detail: "Pick one Insta360 source file before attempting the split fallback.",
      blocker:
        "No source file selected. This MVP only proves the pair-upload browser lane today."
    };
  }

  return {
    ok: false,
    status: "blocked",
    detail:
      "Browser-side single-file Insta360 splitting is not implemented in this MVP.",
    blocker:
      "The repo's proven split/extraction path depends on FFmpeg/libav surfaces that are available on the host machine, but not exposed as a truthful built-in browser API here yet."
  };
}

export function formatFileMeta(file, metadata = {}) {
  if (!file) {
    return "No file loaded";
  }

  const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
  const parts = [`${file.name}`, `${sizeMb} MB`];
  if (metadata.width && metadata.height) {
    parts.push(`${metadata.width}x${metadata.height}`);
  }
  if (Number.isFinite(metadata.duration)) {
    parts.push(`${metadata.duration.toFixed(1)}s`);
  }
  return parts.join(" • ");
}

export function computeLumaPlane(rgba, width, height) {
  const luma = new Uint8Array(width * height);
  for (let rgbaIndex = 0, pixelIndex = 0; pixelIndex < luma.length; rgbaIndex += 4, pixelIndex += 1) {
    luma[pixelIndex] = Math.round(
      rgba[rgbaIndex] * 0.299 +
        rgba[rgbaIndex + 1] * 0.587 +
        rgba[rgbaIndex + 2] * 0.114
    );
  }
  return luma;
}

export function getContainedVideoRect({ containerWidth, containerHeight, videoWidth, videoHeight }) {
  if (
    !Number.isFinite(containerWidth) ||
    !Number.isFinite(containerHeight) ||
    containerWidth <= 0 ||
    containerHeight <= 0
  ) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }

  if (
    !Number.isFinite(videoWidth) ||
    !Number.isFinite(videoHeight) ||
    videoWidth <= 0 ||
    videoHeight <= 0
  ) {
    return { x: 0, y: 0, width: containerWidth, height: containerHeight };
  }

  const scale = Math.min(containerWidth / videoWidth, containerHeight / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;
  return {
    x: (containerWidth - width) / 2,
    y: (containerHeight - height) / 2,
    width,
    height
  };
}

export function getFrameStepDeltaSeconds(frameRate = DEFAULT_FRAME_RATE) {
  const safeFrameRate = Number.isFinite(frameRate) && frameRate > 0 ? frameRate : DEFAULT_FRAME_RATE;
  return 1 / safeFrameRate;
}

export function getSteppedTime({
  currentTime = 0,
  duration = Number.POSITIVE_INFINITY,
  direction = 1,
  frameRate = DEFAULT_FRAME_RATE
}) {
  const delta = getFrameStepDeltaSeconds(frameRate) * (direction < 0 ? -1 : 1);
  const safeCurrentTime = Number.isFinite(currentTime) ? currentTime : 0;
  const safeDuration =
    Number.isFinite(duration) && duration > 0 ? Math.max(0, duration - Number.EPSILON) : Number.POSITIVE_INFINITY;

  return Math.min(safeDuration, Math.max(0, safeCurrentTime + delta));
}

export function projectMotionVector({
  vector,
  analysisWidth,
  analysisHeight,
  displayRect,
  vectorScale = 2.2
}) {
  const scaleX = displayRect.width / analysisWidth;
  const scaleY = displayRect.height / analysisHeight;
  return {
    fromX: displayRect.x + vector.x * scaleX,
    fromY: displayRect.y + vector.y * scaleY,
    toX: displayRect.x + (vector.x + vector.dx * vectorScale) * scaleX,
    toY: displayRect.y + (vector.y + vector.dy * vectorScale) * scaleY
  };
}

export function getMotionFieldCell({
  vector,
  analysisWidth,
  analysisHeight,
  displayRect,
  gridStep = 16
}) {
  const scaleX = displayRect.width / analysisWidth;
  const scaleY = displayRect.height / analysisHeight;
  const cellWidth = Math.max(1, gridStep * scaleX);
  const cellHeight = Math.max(1, gridStep * scaleY);

  return {
    x: displayRect.x + (vector.x - gridStep / 2) * scaleX,
    y: displayRect.y + (vector.y - gridStep / 2) * scaleY,
    width: cellWidth,
    height: cellHeight
  };
}

export function getMotionFieldColor(vector, maximumMagnitude = 1) {
  const magnitude = Math.hypot(vector.dx, vector.dy);
  const clampedMaximum = Math.max(1, maximumMagnitude);
  const normalizedMagnitude = Math.min(1, magnitude / clampedMaximum);
  const direction = Math.atan2(vector.dy, vector.dx);
  const hue = ((direction * 180) / Math.PI + 360) % 360;
  const saturation = 72;
  const lightness = 34 + normalizedMagnitude * 28;
  const alpha = 0.24 + normalizedMagnitude * 0.52;

  return `hsla(${hue.toFixed(1)} ${saturation}% ${lightness.toFixed(1)}% / ${alpha.toFixed(3)})`;
}

export function getMaximumMotionMagnitude(vectors) {
  return vectors.reduce((maximum, vector) => {
    return Math.max(maximum, Math.hypot(vector.dx, vector.dy));
  }, 0);
}

function blockDifference(frameA, frameB, width, blockX, blockY, sampleSize, dx, dy) {
  let score = 0;
  const startX = blockX + dx;
  const startY = blockY + dy;
  for (let localY = 0; localY < sampleSize; localY += 1) {
    const yA = blockY + localY;
    const yB = startY + localY;
    for (let localX = 0; localX < sampleSize; localX += 1) {
      const xA = blockX + localX;
      const xB = startX + localX;
      score += Math.abs(frameA[yA * width + xA] - frameB[yB * width + xB]);
    }
  }
  return score;
}

export function estimateMotionVectors({
  previousFrame,
  currentFrame,
  width,
  height,
  gridStep = 16,
  sampleSize = 10,
  searchRadius = 4,
  minimumConfidence = 18
}) {
  const vectors = [];
  if (!previousFrame || !currentFrame || previousFrame.length !== currentFrame.length) {
    return vectors;
  }

  for (let y = searchRadius; y <= height - sampleSize - searchRadius; y += gridStep) {
    for (let x = searchRadius; x <= width - sampleSize - searchRadius; x += gridStep) {
      const baseline = blockDifference(previousFrame, currentFrame, width, x, y, sampleSize, 0, 0);
      let bestDx = 0;
      let bestDy = 0;
      let bestScore = baseline;

      for (let dy = -searchRadius; dy <= searchRadius; dy += 1) {
        for (let dx = -searchRadius; dx <= searchRadius; dx += 1) {
          const score = blockDifference(previousFrame, currentFrame, width, x, y, sampleSize, dx, dy);
          if (score < bestScore) {
            bestScore = score;
            bestDx = dx;
            bestDy = dy;
          }
        }
      }

      const confidence = baseline - bestScore;
      if (confidence >= minimumConfidence && (bestDx !== 0 || bestDy !== 0)) {
        vectors.push({
          x: x + sampleSize / 2,
          y: y + sampleSize / 2,
          dx: bestDx,
          dy: bestDy,
          confidence
        });
      }
    }
  }

  return vectors;
}

export const FLOW_MODE = "optical-flow-approximation";

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

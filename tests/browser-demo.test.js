import test from "node:test";
import assert from "node:assert/strict";

import {
  computeLumaPlane,
  describeSplitAttempt,
  estimateMotionVectors,
  formatFileMeta
} from "../browser-demo/lib/flow-core.js";

test("describeSplitAttempt returns an explicit blocker without a file", () => {
  const result = describeSplitAttempt();
  assert.equal(result.status, "blocked");
  assert.match(result.blocker, /pair-upload browser lane/i);
});

test("formatFileMeta includes file size and metadata when present", () => {
  const fakeFile = { name: "dual-left.mp4", size: 15 * 1024 * 1024 };
  const text = formatFileMeta(fakeFile, { width: 1920, height: 1080, duration: 29.97 });
  assert.match(text, /dual-left\.mp4/);
  assert.match(text, /15\.0 MB/);
  assert.match(text, /1920x1080/);
  assert.match(text, /30\.0s/);
});

test("computeLumaPlane converts RGBA bytes into grayscale pixels", () => {
  const luma = computeLumaPlane(
    new Uint8ClampedArray([
      255, 0, 0, 255,
      0, 255, 0, 255
    ]),
    2,
    1
  );
  assert.deepEqual(Array.from(luma), [76, 150]);
});

test("estimateMotionVectors detects simple rightward motion", () => {
  const width = 32;
  const height = 32;
  const previous = new Uint8Array(width * height);
  const current = new Uint8Array(width * height);

  for (let y = 10; y < 18; y += 1) {
    for (let x = 10; x < 18; x += 1) {
      previous[y * width + x] = 255;
      current[y * width + x + 2] = 255;
    }
  }

  const vectors = estimateMotionVectors({
    previousFrame: previous,
    currentFrame: current,
    width,
    height,
    gridStep: 8,
    sampleSize: 6,
    searchRadius: 3,
    minimumConfidence: 10
  });

  assert.ok(vectors.length > 0);
  assert.ok(vectors.some((vector) => vector.dx >= 1));
});

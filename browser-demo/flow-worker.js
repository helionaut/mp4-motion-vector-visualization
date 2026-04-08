import { estimateMotionVectors } from "./lib/flow-core.js";

self.onmessage = (event) => {
  const { id, payload } = event.data;
  const vectors = estimateMotionVectors(payload);
  self.postMessage({
    id,
    vectors
  });
};

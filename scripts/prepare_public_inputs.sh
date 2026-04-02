#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
FFPROBE_BIN=$("$SCRIPT_DIR/bootstrap_media_tools.sh")

python3 "$SCRIPT_DIR/prepare_inputs.py" \
  --config "$REPO_ROOT/configs/input_sets/public-baseline.json" \
  --manifest-out "$REPO_ROOT/manifests/public-baseline.json" \
  --ffprobe-bin "$FFPROBE_BIN" \
  "$@"

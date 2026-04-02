#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
FFPROBE_BIN=$("$SCRIPT_DIR/bootstrap_media_tools.sh")

CONFIG_PATH="${MP4_MV_PRIVATE_INPUT_CONFIG:-$REPO_ROOT/configs/input_sets/private-template.json}"
MANIFEST_OUT="${MP4_MV_PRIVATE_MANIFEST_OUT:-$REPO_ROOT/manifests/user-validation.json}"

python3 "$SCRIPT_DIR/prepare_inputs.py" \
  --config "$CONFIG_PATH" \
  --manifest-out "$MANIFEST_OUT" \
  --ffprobe-bin "$FFPROBE_BIN" \
  "$@"

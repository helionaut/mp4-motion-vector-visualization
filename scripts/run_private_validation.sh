#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
MANIFEST_OUT="${MP4_MV_PRIVATE_MANIFEST_OUT:-$REPO_ROOT/manifests/user-validation.json}"

"$SCRIPT_DIR/prepare_private_inputs.sh" "$@"
python3 "$SCRIPT_DIR/public_baseline.py" run --manifest "$MANIFEST_OUT"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
RESEARCH_CONTEXT="$REPO_ROOT/.symphony/research-context.json"

if [[ -f "$RESEARCH_CONTEXT" ]]; then
  CACHE_ROOT=$(python3 - <<'PY' "$RESEARCH_CONTEXT"
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    print(json.load(fh)["cacheRoot"])
PY
)
else
  CACHE_ROOT="${MP4_MV_CACHE_ROOT:-/home/helionaut/srv/research-cache/18afd661ce11}"
fi

TOOLCHAINS_DIR="$CACHE_ROOT/toolchains"
ARCHIVE_URL="${MP4_MV_FFMPEG_ARCHIVE_URL:-https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz}"
ARCHIVE_NAME=$(basename "$ARCHIVE_URL")
ARCHIVE_PATH="$TOOLCHAINS_DIR/$ARCHIVE_NAME"
INSTALL_DIR="$TOOLCHAINS_DIR/ffmpeg-johnvansickle-static"
FFPROBE_PATH="$INSTALL_DIR/ffprobe"
FFMPEG_PATH="$INSTALL_DIR/ffmpeg"

if [[ -x "$FFPROBE_PATH" && -x "$FFMPEG_PATH" ]]; then
  printf '%s\n' "$FFPROBE_PATH"
  exit 0
fi

mkdir -p "$TOOLCHAINS_DIR"

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  curl -L "$ARCHIVE_URL" -o "$ARCHIVE_PATH"
fi

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
tar -xJf "$ARCHIVE_PATH" -C "$tmp_dir"

extracted_dir=$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [[ -z "$extracted_dir" ]]; then
  echo "Could not locate extracted FFmpeg directory in $tmp_dir" >&2
  exit 1
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp "$extracted_dir/ffprobe" "$INSTALL_DIR/ffprobe"
cp "$extracted_dir/ffmpeg" "$INSTALL_DIR/ffmpeg"
chmod +x "$INSTALL_DIR/ffprobe" "$INSTALL_DIR/ffmpeg"

printf '%s\n' "$FFPROBE_PATH"

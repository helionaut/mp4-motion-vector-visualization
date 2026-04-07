#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_FILE="$REPO_ROOT/tools/host_libavcodec_mv_extractor.c"
OUTPUT_FILE="${REPO_ROOT}/build/host/libavcodec_mv_extractor"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "missing extractor source: $SOURCE_FILE" >&2
  exit 1
fi

if ! command -v gcc >/dev/null 2>&1; then
  echo "missing required tool: gcc" >&2
  exit 1
fi

if ! command -v pkg-config >/dev/null 2>&1; then
  echo "missing required tool: pkg-config" >&2
  exit 1
fi

if ! pkg-config --exists libavformat libavcodec libavutil; then
  echo "missing pkg-config entries for libavformat/libavcodec/libavutil" >&2
  echo "install the FFmpeg development packages for this host before rerunning the host extractor slice" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"
gcc \
  -std=c11 \
  -O2 \
  -Wall \
  -Wextra \
  -o "$OUTPUT_FILE" \
  "$SOURCE_FILE" \
  $(pkg-config --cflags --libs libavformat libavcodec libavutil) \
  -lm

echo "$OUTPUT_FILE"

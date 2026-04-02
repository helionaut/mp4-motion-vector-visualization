#!/usr/bin/env bash

set -euo pipefail

prd_path="${1:-docs/PRD.md}"

if [[ ! -f "$prd_path" ]]; then
  echo "Missing PRD file: $prd_path" >&2
  exit 1
fi

required_patterns=(
  "^# Product Requirements Document: MP4 Motion Vector Visualization$"
  "^## Document intent$"
  "^## Project intent$"
  "^## Problem being tested$"
  "^## Hypothesis$"
  "^## Integration goal$"
  "^## Target user and stakeholders$"
  "^## In-scope outcome for this PRD$"
  "^## Source inputs$"
  "^## Prepared artifacts$"
  "^## Workflow contract$"
  "^## Success metrics$"
  "^## Failure criteria$"
  "^## Acceptance evidence$"
  "^## Non-goals$"
  "^## Risks and unresolved questions$"
  "^## Final deliverables for this issue$"
  "Build a research workflow to ingest two MP4 files, extract codec motion"
  "vectors, and visualize and compare them\\."
)

for pattern in "${required_patterns[@]}"; do
  if ! grep -Eq "$pattern" "$prd_path"; then
    echo "PRD contract check failed: missing pattern: $pattern" >&2
    exit 1
  fi
done

echo "PRD contract check passed for $prd_path"

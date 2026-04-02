# Research Contract

Project: MP4 Motion Vector Visualization

## Strategic goal

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Current answer state

- Overall verdict: `open`
- Highest-value unanswered question: _fill this in during PRD / experiment-contract work_

## Reusable baseline

- Known-good public baseline: _not established yet_
- Known-good private/user-data baseline: _not established yet_
- Reusable build/tooling baseline: _not established yet_
- Shared cache root: `~/srv/research-cache/mp4-motion-vector-visualization`

## Experiment ledger rules

Every research/build/run issue should leave behind a compact tactical + strategic handoff in this file or in a linked report:

- what is already proven
- what is still blocked
- what exact variable changes next
- what success would look like
- what abort condition ends the attempt
- which artifacts, binaries, datasets, or reports the next agent should reuse

Do not let the project drift into generic follow-up tickets. Every next issue should name the concrete stage and changed variable.

## Follow-up issue contract

Use this compact shape for future research follow-up issues:

### Strategic context
- one paragraph on why this step matters for the project hypothesis

### Tactical next step
- the one blocker or question this issue attacks directly

### Reuse from previous work
- committed scripts, reports, paths, binaries, datasets, or cache dirs the next agent should start from

### Changed variable
- the one variable that changes in this attempt

### Hypothesis
- what we expect to learn if this attempt succeeds or fails

### Success criterion
- the concrete observable result that counts as success

### Abort condition
- when to stop retrying and write up the blocker instead of looping

### Outputs
- which report, binary provenance, artifact, PR, or document must exist when the issue finishes

# External Inputs Contract: MP4 Motion Vector Visualization

Status: Draft
Last Updated: bootstrap

## Project Intent

Build a research workflow to ingest two MP4 files, extract codec motion vectors, and visualize/compare them.

## Purpose

This document is the source of truth for every external, private, or user-supplied
input the project needs. Its job is to let agents move forward autonomously.

Rules:
- If raw assets already exist, the next step is to adapt them into the required
  tool format. That is implementation work, not a reason to stop.
- Only list something as "missing" if the source-of-truth asset, secret, or
  non-derivable fact is genuinely absent.
- Any required download, bootstrap, extraction, conversion, or preprocessing
  step should be scripted or documented in repo-local commands.

## Source Inputs

List the highest-fidelity assets already provided or expected here.

Example fields:
- source name
- where it arrived from
- whether it is private/local-only
- current path or retrieval command
- notes on trust level or provenance

## Prepared Artifacts

List the exact artifacts downstream tasks actually consume.

Example fields:
- prepared artifact name
- generator script or command
- output path
- validation command
- downstream tasks that depend on it

## Deterministic Paths

Use stable repo-local locations whenever possible.

Suggested conventions:
- raw/private inputs: `datasets/user/raw/`
- prepared/private artifacts: `datasets/user/prepared/`
- checked-in shareable fixtures: `datasets/fixtures/`
- calibration/config bundles: `configs/`
- manifests describing prepared runs: `manifests/`
- logs and reports: `logs/out/` and `reports/out/`

## Bootstrap And Acquisition

Document every required external tool, download, or setup step here.

Each step should answer:
- what is needed
- how the repo installs or fetches it
- how to verify it is ready

## Real Gaps

Only unresolved blockers belong here.

Each gap should say:
- what is truly missing
- why it cannot be derived from existing raw assets
- who can resolve it
- which downstream task is blocked

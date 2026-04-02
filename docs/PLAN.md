# Execution Plan

Project: MP4 Motion Vector Visualization
Issue: HEL-147

## Goal

Build a reproducible research workflow that:

1. accepts two MP4 inputs
2. extracts codec motion-vector data from each file
3. renders visual overlays and summary comparisons
4. produces artifacts future agents can rerun without rediscovering the environment

## Scope For The First Project Pass

In scope:
- define the reproducible environment contract for media analysis
- define the input contract for two MP4 sources and their prepared derivatives
- prove a known-good extraction baseline on at least one public sample pair
- define the comparison output surface: raw vectors, overlay render, and comparison summary
- leave a follow-up lane for user/private-data validation once the public baseline is stable

Out of scope for the intake ticket:
- inventing a new codec parser before testing FFmpeg-side extraction
- polishing a user-facing application before the extraction baseline is proven
- claiming private-data support before the input contract and baseline run exist

## Research Questions

1. Which extractor path gives a stable motion-vector representation from MP4 inputs on this stack?
2. What minimal metadata must be preserved per frame to support visual comparison?
3. What output artifacts are enough to compare two videos credibly without overbuilding the UI?
4. Which parts of the workflow belong in the shared research cache versus the disposable issue workspace?

## Execution Sequence

1. HEL-148: write the PRD and experiment contract
2. HEL-149: lock the Docker environment, media tooling, and cache mount strategy
3. HEL-150: define raw input locations, prepared artifact paths, and readiness checks for two MP4 files
4. HEL-151: establish a public known-good baseline that extracts motion vectors and renders a first comparison artifact
5. HEL-152: rerun the same workflow on user/private data and record any delta from the public baseline
6. HEL-153: summarize findings, remaining risks, and the next recommended implementation slice

## Deliverables Expected From The Baseline Lane

- a repo-local command that ingests two MP4 paths deterministically
- extracted per-frame motion-vector data in a stable machine-readable format
- at least one rendered visualization artifact per input
- one comparison artifact that highlights directional or magnitude differences
- a report that states what is proven, what is still blocked, and which variable changes next

## Issue Pack

| Issue | Purpose | Exit signal |
| --- | --- | --- |
| HEL-148 | Convert the intake into a PRD plus experiment contract. | Success criteria and abort conditions are explicit. |
| HEL-149 | Make the research environment reproducible with Docker and shared cache usage. | A future agent can run the same baseline without re-bootstrap guesswork. |
| HEL-150 | Capture the MP4 input contract and preparation steps. | Two MP4 inputs can be located, prepared, and checked consistently. |
| HEL-151 | Prove extraction and visualization on public inputs. | Motion vectors are extracted and at least one comparison artifact exists. |
| HEL-152 | Validate the workflow against user/private inputs. | Any private-data-specific gaps are isolated and documented. |
| HEL-153 | Synthesize the outcome and recommend the next slice. | The project has a grounded next-step recommendation. |

## First Next Actions

- Start with FFmpeg-backed extraction before considering lower-level codec tooling.
- Use public sample MP4s first so the extraction lane can be proven without waiting on private assets.
- Treat the first comparison output as a research artifact, not a polished product surface.
- Keep the changed variable narrow on each issue: environment, inputs, extraction baseline, private-data validation, then synthesis.

## Definition Of Done For HEL-147

- project scope is explicit about what will and will not be proven first
- the initial issue pack has a clear order and exit signal
- the next Symphony agent can start HEL-148 or HEL-149 without re-reading this ticket thread

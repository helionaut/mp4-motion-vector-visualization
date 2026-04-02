# Product Requirements Document: MP4 Motion Vector Visualization

## Document intent

This document is the experiment and validation contract for the first research
slice of the project. It defines what must be proven, what inputs and artifacts
the workflow requires, and which observable results count as success or failure.

## Project intent

Build a research workflow to ingest two MP4 files, extract codec motion
vectors, and visualize and compare them.

This is not a generic browser-app brief. The primary output is a reproducible
workflow and evidence package that shows whether the motion-vector extraction
and comparison approach is viable on real MP4 inputs.

## Problem being tested

Teams working with encoded video need a way to inspect motion at the codec
level without guessing from rendered pixels alone. Today there is no established
project workflow in this repository that can:

1. take two MP4 files as explicit inputs
2. extract codec motion vectors from each file
3. prepare comparable artifacts from those vectors
4. produce a visualization and comparison output that can be reviewed by a
human operator

The work in this issue should define the contract for proving that workflow is
real, reproducible, and useful enough to justify the next implementation slices.

## Hypothesis

If the project can ingest two MP4 files and reliably extract motion-vector data
from both into a normalized intermediate representation, then a reproducible
visual comparison workflow can be built that makes codec-level motion behavior
observable and comparable between the two videos.

## Integration goal

Create a stable research lane that future issues can implement in stages:

1. input acquisition and validation
2. motion-vector extraction
3. artifact normalization
4. visualization generation
5. side-by-side comparison and outcome reporting

Success for this issue is the contract that defines those stages, not the full
implementation of them.

## Target user and stakeholders

- Primary operator: an engineer or researcher running repeatable local or
containerized experiments on MP4 files
- Primary reviewer: a project stakeholder evaluating whether extracted motion
vector data is trustworthy and useful for comparison
- Downstream consumers: future agents implementing environment setup, input
readiness, baseline validation, user-data validation, and outcome synthesis

## In-scope outcome for this PRD

This PRD must make the following explicit:

- what source inputs are required
- what prepared artifacts downstream steps consume
- what hypothesis the workflow is testing
- what outputs reviewers should expect
- which metrics and evidence determine success or failure
- which risks, unknowns, and non-goals remain open

## Source inputs

The experiment contract assumes these required inputs:

| Input | Requirement | Notes |
| --- | --- | --- |
| MP4 A | Required | One source video used as the first comparison target |
| MP4 B | Required | One source video used as the second comparison target |
| Input manifest | Required | Stable metadata describing file paths, provenance, codec details if known, and the comparison run id |
| Extraction configuration | Required | Flags or tool settings that determine how motion vectors are extracted and serialized |

Input expectations:

- Both primary inputs must be MP4 files available to the workflow at stable,
documented paths.
- The workflow must preserve provenance for each input so reviewers know which
video produced which extracted artifacts.
- The contract does not assume the two MP4 files share the same resolution,
duration, bitrate, or content, but any mismatch that weakens comparison quality
must be surfaced in the evidence.

## Prepared artifacts

The workflow should produce or require these prepared artifacts:

| Artifact | Purpose | Minimum acceptance requirement |
| --- | --- | --- |
| Input manifest | Declares the run inputs and provenance | Names both MP4 files and the run identifier |
| Motion-vector extraction output for MP4 A | Raw or semi-structured vector data | Non-empty and attributable to MP4 A |
| Motion-vector extraction output for MP4 B | Raw or semi-structured vector data | Non-empty and attributable to MP4 B |
| Normalized comparison-ready representation | Makes outputs comparable despite tool-specific raw formats | Documents schema or field mapping used for comparison |
| Visualization artifact(s) | Lets a human inspect motion-vector behavior | Clearly tied to each input and comparison run |
| Comparison report | Summarizes observed differences, anomalies, and limits | Includes success/failure verdict and evidence links |

Suggested stable locations:

- raw inputs: `datasets/user/raw/`
- prepared artifacts: `datasets/user/prepared/`
- manifests: `manifests/`
- reports: `reports/out/`
- logs: `logs/out/`

## Workflow contract

The intended research workflow is:

1. Ingest two MP4 paths and validate that both files are readable.
2. Capture run metadata and input provenance in a manifest.
3. Extract codec motion vectors from each MP4 with a reproducible toolchain.
4. Normalize or annotate the extracted outputs enough to support comparison.
5. Generate visual outputs and a comparison report for human review.
6. Record whether the run met the success contract or failed for a concrete
reason.

## Success metrics

This research slice should define later implementation success with measurable
criteria:

| Area | Success metric |
| --- | --- |
| Input readiness | Two declared MP4 inputs can be resolved and processed in one run |
| Extraction viability | Motion-vector extraction completes for both files without silent fallback to empty output |
| Artifact quality | Each input produces non-empty artifacts with preserved provenance |
| Comparison readiness | Extracted outputs can be mapped into a comparison-ready representation |
| Visualization usefulness | Reviewers can identify which visualization belongs to which input and compare them side by side |
| Reproducibility | Another agent can rerun the same command and regenerate the same class of artifacts from the same inputs |

## Failure criteria

The experiment should be treated as failed if any of the following occur:

- either MP4 input cannot be ingested or validated
- extraction works for only one input
- extracted motion-vector output is empty, malformed, or not attributable to a
specific source file
- the workflow depends on manual, undocumented preparation steps
- the produced artifacts cannot support side-by-side comparison
- visual outputs exist but do not let a reviewer understand what was compared or
what the extracted vectors represent
- reproducibility depends on unstated host-only conditions, ad hoc downloads, or
missing private context

## Acceptance evidence

This issue should be considered complete when the repository contains a PRD
that future implementation tickets can treat as source-of-truth and that names
the evidence required from those tickets.

Expected evidence from downstream implementation issues:

- documented input contract for the two MP4 files and their provenance
- reproducible environment contract for the extraction toolchain
- at least one known-good run producing artifacts for two MP4 inputs
- saved visualization outputs and a comparison report
- a validation record naming the exact command used and produced artifacts

## Non-goals

The following are explicitly out of scope for this issue:

- shipping a polished end-user application
- solving every codec/container edge case
- guaranteeing semantic correctness of the encoder's motion estimation itself
- proving research value on every possible MP4 source type
- building long-term storage, deployment, or multi-user collaboration surfaces
- defining product-market requirements beyond the experiment contract

## Risks and unresolved questions

- Some MP4 files may not expose motion vectors in a way the chosen extraction
tool can recover.
- Comparison quality may degrade when the two files differ substantially in
codec, frame rate, resolution, or GOP structure.
- Visualization may require additional normalization decisions before outputs
become reviewable.
- Tooling may expose raw vectors in a format that is technically complete but
not yet human-legible.
- Private or user-provided MP4 inputs may be required to prove the intended
research value beyond public fixtures.

## Final deliverables for this issue

- `docs/PRD.md` committed as the source-of-truth experiment contract
- clear linkage between this PRD and the existing environment, research, and
input contract docs
- enough specificity that follow-up issues can implement and validate the
workflow without redefining the hypothesis or success criteria

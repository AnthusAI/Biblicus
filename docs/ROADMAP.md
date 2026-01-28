# Roadmap

This document is the ordered plan for what to build next.

If you are looking for runnable examples, see `docs/NEXT_STEPS.md`.

## Principles

- Behavior specifications are the authoritative definition of behavior.
- Every behavior that exists is specified.
- Validation and documentation are part of the product.
- Raw corpus items remain readable, portable files.
- Derived artifacts are stored under the corpus and can coexist for multiple implementations.

## Current state

Version zero includes:

- A file based corpus with ingestion, catalog rebuild, import, ignore rules, and lifecycle hooks.
- A retrieval baseline (`scan`) and a practical local backend (`sqlite-full-text-search`).
- A separate text extraction stage with extraction runs and a composable extractor pipeline.

## Milestones

### Milestone 1: Portable Document Format text extraction plugin

Goal: extract usable text from Portable Document Format items without mutating raw corpus files.

Deliverables:

- A new extractor plugin that produces extracted text artifacts for Portable Document Format items.
- A dataset and evaluation approach that compares extractor outputs for accuracy, speed, and cost.

Acceptance checks:

- New behavior specifications describe the supported Portable Document Format subset.
- `python3 scripts/test.py` reports 100 percent coverage.
- `python3 scripts/test.py --integration` downloads sample Portable Document Format files and produces extracted text artifacts.

### Milestone 2: Optical character recognition plugin

Goal: extract usable text from image items as derived artifacts, with pluggable providers.

Deliverables:

- One local reference implementation, even if it is limited.
- A provider interface that can be backed by a local engine or a remote service.
- Evaluation metrics that report throughput and error rates.

Acceptance checks:

- A small corpus of test images can be downloaded by an integration script.
- Extraction runs record success, empty output, and skip counts per item.

### Milestone 3: Evidence quality stages

Goal: add explicit rerank and filter stages to retrieval.

Deliverables:

- A rerank stage interface that takes evidence and returns reordered evidence.
- A filter stage interface that applies metadata and source constraints.
- Documentation that explains how to configure budgets and stage ordering.

Acceptance checks:

- Behavior specs cover the new stages.
- Evaluation reports show per stage metrics and final metrics.

### Milestone 4: Evaluation reports and datasets

Goal: make evaluation results easier to interpret and compare.

Deliverables:

- A dataset authoring workflow that supports small hand labeled sets and larger synthetic sets.
- A report that includes per query diagnostics and a clear summary.

Acceptance checks:

- The existing dataset format remains stable or is versioned.
- Reports remain deterministic for the same inputs.

### Milestone 5: Pluggable backend hosting modes

Goal: add one reference backend in an external process or remote service mode.

Deliverables:

- A tool server that exposes a backend through a stable interface.
- Documentation that shows how to run a backend out of process and connect to it.

Acceptance checks:

- Local tests remain fast and deterministic.
- Integration tests validate end to end retrieval through the tool boundary.

## Where to put design notes

Design notes live in `docs/` so they are easy to browse and cross link.

Executable behavior lives in `features/*.feature`.


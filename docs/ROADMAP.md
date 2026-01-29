# Roadmap

This document is the ordered plan for what to build next.

If you are looking for runnable examples, see `docs/DEMOS.md`.

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
- Selection extractor steps that choose extracted text within a pipeline.
- A speech to text extractor plugin (`stt-openai`) implemented as an optional dependency.
- An optical character recognition extractor plugin (`ocr-rapidocr`) implemented as an optional dependency.
- A broad catchall extractor plugin (`unstructured`) implemented as an optional dependency.
- Integration corpora that include deterministic non-text cases such as a blank Portable Document Format file and a silence Waveform Audio File Format clip.

Milestones 1 through 4 are complete. The next planned work begins at Milestone 5.

## Near-term focus

The next work will focus on the retrieval side of the pipeline:

- Make retrieval runs and evidence production the simplest possible practical “minimum viable product”.
- Add explicit evidence quality stages (rerank and filter) that are easy to compose, test, and evaluate.
- Expand retrieval evaluation so it is easy to compare backends using the same corpora and datasets.

Lower-priority work related to corpus ingestion conveniences and extractor evaluation remains valuable, but it is deferred while we make retrieval practical end to end.

## Milestones

### Milestone 1: Artifact lifecycle and storage layout

Goal: make derived artifacts easy to inspect, compare, and retain across multiple extraction implementations.

Status: complete.

Deliverables:

- A stable on-disk layout for extracted artifacts that partitions by extraction recipe and extractor identity.
- A clear, human-readable manifest for each extraction run that includes configuration, timing, and summary stats.
- Corpus-level tooling to list, inspect, and delete derived artifacts without touching raw items.

Acceptance checks:

- Raw items remain readable, portable files in `raw/`.
- Derived artifacts can coexist for multiple extractors and multiple recipes over the same raw items.
- Behavior specifications cover artifact layout and lifecycle operations.

### Milestone 2: Idempotency and change detection

Goal: make extraction runs repeatable, fast, and safe by skipping work when nothing relevant changed.

Status: complete.

Deliverables:

- Change detection for extraction inputs (raw bytes identity) and extraction settings (extractor identity and configuration).
- Extraction run behavior that cleanly separates “skipped because already present” from “skipped because unsupported”.
- A simple “rebuild” workflow that is explicit and safe: delete an extraction run, then build it again.

Acceptance checks:

- Running the same extraction recipe twice produces the same outputs and reports predictable skip counts.
- Behavior specifications cover idempotency and change detection outcomes.

### Milestone 3: Failure semantics and reporting

Goal: make extraction outcomes diagnosable and measurable without reading log output.

Status: complete.

Deliverables:

- A clear set of extraction outcome categories (success, empty output, skipped, fatal error) with structured reasons.
- Per-run reporting that summarizes outcomes and provides a path to per-item details.
- Consistent, user-facing errors when optional dependencies or required configuration are missing.

Acceptance checks:

- Behavior specifications cover error classification and summary reporting.
- Reports remain deterministic for the same corpus and recipe.

### Milestone 4: Corpus import and crawl utilities

Goal: make it easy to build a corpus from real-world sources while keeping the corpus readable and portable.

Status: complete.

Deliverables:

- Folder tree import ergonomics: stable naming, media type detection, and predictable metadata sidecars.
- A website crawl command that stays within an allow-listed uniform resource locator prefix and respects `.biblicusignore`.
- Integration downloads that produce a small, realistic, repeatable corpus for experimentation without committing third-party content to the repository.

Acceptance checks:

- The crawl and import workflows are fully specified with behavior specifications.
- Integration corpora remain gitignored, and can be regenerated from scripts.

### Milestone 6: Evidence quality stages

Goal: add explicit rerank and filter stages to retrieval.

Status: next.

Deliverables:

- A rerank stage interface that takes evidence and returns reordered evidence.
- A filter stage interface that applies metadata and source constraints.
- Documentation that explains how to configure budgets and stage ordering.

Acceptance checks:

- Behavior specs cover the new stages.
- Evaluation reports show per stage metrics and final metrics.

### Milestone 7: Evaluation reports and datasets

Goal: make evaluation results easier to interpret and compare.

Status: next.

Deliverables:

- A dataset authoring workflow that supports small hand labeled sets and larger synthetic sets.
- A report that includes per query diagnostics and a clear summary.

Acceptance checks:

- The existing dataset format remains stable or is versioned.
- Reports remain deterministic for the same inputs.

### Milestone 8: Pluggable backend hosting modes

Goal: add one reference backend in an external process or remote service mode.

Status: later.

Deliverables:

- A tool server that exposes a backend through a stable interface.
- Documentation that shows how to run a backend out of process and connect to it.

Acceptance checks:

- Local tests remain fast and deterministic.
- Integration tests validate end to end retrieval through the tool boundary.

## Where to put design notes

Design notes live in `docs/` so they are easy to browse and cross link.

Executable behavior lives in `features/*.feature`.

## Completed milestones (version zero)

These milestones are complete as of version zero, and are maintained through behavior specifications:

- Portable Document Format text extraction (`pdf-text`).
- Optical character recognition extraction (`ocr-rapidocr`).
- Catchall extraction for wide format coverage (`unstructured`).
- Selection extractor steps (`select-text`, `select-longest-text`).

## Completed milestones (post version zero)

These milestones are complete after version zero, and remain defined by behavior specifications:

- Extraction run lifecycle operations (`extract list`, `extract show`, `extract delete`) and a stable artifact layout.
- Deterministic extraction run identifiers based on recipe and catalog version (idempotent extraction runs).
- Crawl ingestion (`crawl`) with allow-listed prefix enforcement and `.biblicusignore` filtering.

## Deferred milestones

These milestones remain planned, but are not the near-term focus.

### Milestone 5: Extractor datasets and evaluation harness (deferred)

Goal: compare extraction approaches in a way that is measurable, repeatable, and useful for practical engineering decisions.

Deliverables:

- Dataset authoring workflow for extraction ground truth (for example: expected transcripts and expected optical character recognition text).
- Evaluation metrics for accuracy, speed, and cost, including “processable fraction” for a given extractor recipe.
- A report format that can compare multiple extraction recipes against the same corpus and dataset.

Acceptance checks:

- Evaluation results are stable and reproducible for the same corpus and dataset inputs.
- Reports make it clear when an extractor fails to process an item versus producing empty output.

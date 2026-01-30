# Roadmap

This document describes what we plan to build next.

If you are looking for runnable examples, see `docs/DEMOS.md`.

If you are looking for what already exists, start with:

- `docs/FEATURE_INDEX.md` for a map of features to behavior specifications and modules.
- `CHANGELOG.md` for released changes.

## Principles

- Behavior specifications are the authoritative definition of behavior.
- Every behavior that exists is specified.
- Validation and documentation are part of the product.
- Raw corpus items remain readable, portable files.
- Derived artifacts are stored under the corpus and can coexist for multiple implementations.

## Completed foundations

These are the capability slices that already exist and have end-to-end behavior specifications.

### Retrieval evaluation and datasets

- Dataset authoring workflow for small hand-labeled sets and larger synthetic sets.
- Evaluation reports with per-query diagnostics and summary metrics.
- Versioned dataset formats and deterministic reports for stable inputs.

### Retrieval quality upgrades

- Tuned lexical baseline with BM25, n-gram range controls, and stop word policies.
- Reranking stage for top-N candidates with explicit stage metadata.
- Hybrid retrieval with explicit fusion weights and stage-level scores.

### Context pack policy surfaces

- Policy variants for formatting, ordering, and metadata inclusion.
- Token and character budget strategies with explicit selectors.
- Documentation and examples that show how policy choices change outputs.

## Next: extraction evaluation harness

Goal: compare extraction approaches in a way that is measurable, repeatable, and useful for practical engineering decisions.

Deliverables:

- Dataset authoring workflow for extraction ground truth (for example: expected transcripts and expected OCR text).
- Evaluation metrics for accuracy, speed, and cost, including processable fraction for a given extractor recipe.
- A report format that can compare multiple extraction recipes against the same corpus and dataset.

Acceptance checks:

- Evaluation results are stable and reproducible for the same corpus and dataset inputs.
- Reports make it clear when an extractor fails to process an item versus producing empty output.

## Next: corpus analysis tools

Goal: provide lightweight analysis utilities that summarize corpus themes and guide curation.

Deliverables:

- Basic corpus profiling with deterministic metrics for raw items and extracted text.
- Hidden Markov modeling analysis for sequence-driven corpora.
- A way to compare analysis outputs across corpora or corpus snapshots.

Acceptance checks:

- Analysis is reproducible for the same corpus state.
- Reports are exportable and readable without custom tooling.

## Later: alternate backends and hosting modes

Goal: broaden the backend surface while keeping the core predictable.

Deliverables:

- A second backend with different performance tradeoffs.
- A tool server that exposes a backend through a stable interface.
- Documentation that shows how to run a backend out of process.

Acceptance checks:

- Local tests remain fast and deterministic.
- Integration tests validate retrieval through the tool boundary.

## Deferred: corpus and extraction work

These are valuable, but intentionally not the near-term focus while retrieval becomes practical end to end.

### In-memory corpus for ephemeral workflows

Goal: allow programmatic, temporary corpora that live in memory for short-lived agents or tests.

Deliverables:

- A memory-backed corpus implementation that supports the same ingestion and catalog APIs.
- A serialization option for snapshots so ephemeral corpora can be persisted when needed.
- Documentation that explains tradeoffs versus file-based corpora.

Acceptance checks:

- Behavior specifications cover ingestion, listing, and reindexing in memory.
- Retrieval and extraction can operate on the in-memory corpus without special casing.

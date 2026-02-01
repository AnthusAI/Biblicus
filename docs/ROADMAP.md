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

### Extraction evaluation harness

This evaluation harness compares extraction approaches in a way that is measurable, repeatable, and useful for
practical engineering decisions.

### Corpus analysis tools

Lightweight analysis utilities summarize corpus themes and guide curation:

- Basic corpus profiling with deterministic metrics for raw items and extracted text.
- Topic modeling with BERTopic and optional LLM-assisted labeling.
- Side-by-side analysis outputs stored under the corpus for reproducible comparison.

### Sequence analysis (Markov analysis)

Goal: provide a sequence-oriented analysis backend for corpora where order matters (conversations, timelines, logs).

Deliverables:

- Markov analysis for sequence-driven corpora (including hidden Markov models where appropriate).
- A report format that explains state transitions and emissions with evidence.
- Evaluation guidance for comparing HMM outputs across corpora or snapshots.

Acceptance checks:

- HMM analysis is reproducible for the same corpus state and extraction run.
- Reports are exportable and readable without custom tooling.

### Text utilities

Small, reusable building blocks for transforming text in ways that are hard to do reliably with one-shot generation.

Deliverables:

- Text extraction and slicing utilities that operate via a virtual file editing tool loop.
- Optional higher-level utilities built on the same pattern (annotation, linking, redaction).
- Documentation and runnable demos that show the mechanism and how to use each utility.

Acceptance checks:

- Utilities have end-to-end behavior specifications and are fully covered by tests.
- Integration tests can be run against real model APIs when configured.

## Next: Tactus integration

Goal: make Biblicus usable from durable agent workflows without baking assistant logic into Biblicus itself.

Deliverables:

- A Model Context Protocol (MCP) toolset surface for Biblicus (ingest, query, stats, and evidence retrieval).
- Clear dependency wiring for secrets and network access (in-sandbox vs brokered).
- One reference procedure demonstrating retrieval-augmented generation built on Biblicus evidence outputs.

Acceptance checks:

- Tools expose evidence-first outputs with stable schemas.
- Procedures remain in control of prompting and context budgeting policy.

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

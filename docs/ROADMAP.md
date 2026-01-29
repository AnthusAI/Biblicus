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

## Next: retrieval evaluation and datasets

Goal: make evaluation results easier to interpret and compare.

Deliverables:

- A dataset authoring workflow that supports small hand-labeled sets and larger synthetic sets.
- A report that includes per-query diagnostics and a clear summary.

Acceptance checks:

- Dataset formats are versioned when they change.
- Reports remain deterministic for the same inputs.

## Next: context pack policy surfaces

Goal: make context shaping policies easier to evaluate and swap.

Deliverables:

- A clear set of context pack policy variants (formatting, ordering, metadata inclusion).
- Token budget strategies that can use a real tokenizer.
- Documentation that explains where context shaping fits in the pipeline.

Acceptance checks:

- Behavior specifications cover policy selection and budgeting behaviors.
- Example outputs show how context packs differ across policies.

## Next: extraction backends (OCR and document understanding)

Goal: treat optical character recognition and document understanding as pluggable extractors with consistent inputs and outputs.

Deliverables:

- A baseline OCR extractor that is fast and local for smoke tests.
- A higher quality OCR extractor candidate (for example: Paddle OCR or Docling OCR).
- A general document understanding extractor candidate (for example: Docling or Unstructured).
- A consistent output contract that captures text plus optional confidence and per-page metadata.
- A selector policy for choosing between multiple extractor outputs in a pipeline.
- A shared evaluation harness for extraction backends using the same corpus and dataset.

Acceptance checks:

- Behavior specifications cover extractor selection and output provenance.
- Evaluation reports compare accuracy, processable fraction, latency, and cost.

## Next: corpus analysis tools

Goal: provide lightweight analysis utilities that summarize corpus themes and guide curation.

Deliverables:

- A topic modeling workflow for corpus analysis (for example: BERTopic).
- A report that highlights dominant themes and outliers.
- A way to compare topic distributions across corpora or corpus snapshots.

Acceptance checks:

- Analysis is reproducible for the same corpus state.
- Reports are exportable and readable without custom tooling.

### Candidate backend ecosystem (for planning and evaluation)

Document understanding and OCR blur together at the interface level in Biblicus, so the roadmap treats them as extractor candidates with the same input/output contract.

Docling family candidates:

- Docling (document understanding with structured outputs)
- docling-ocr (OCR component in the Docling ecosystem)

General-purpose extraction candidates:

- Unstructured (element-oriented extraction for many formats)
- MarkItDown (lightweight conversion to Markdown)
- Kreuzberg (speed-focused extraction for bulk workflows)
- ExtractThinker (schema-driven extraction using Pydantic contracts)

Ecosystem adapters:

- LangChain document loaders (uniform loader interface across many sources)

### Guidance for choosing early targets

- If you need layout and table understanding, prioritize Docling and docling-ocr.
- If you need speed and simplicity, prioritize MarkItDown or Kreuzberg.
- If you need schema-first extraction, prioritize ExtractThinker layered on an OCR or document extractor.

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

### Extractor datasets and evaluation harness

Goal: compare extraction approaches in a way that is measurable, repeatable, and useful for practical engineering decisions.

Deliverables:

- Dataset authoring workflow for extraction ground truth (for example: expected transcripts and expected optical character recognition text).
- Evaluation metrics for accuracy, speed, and cost, including “processable fraction” for a given extractor recipe.
- A report format that can compare multiple extraction recipes against the same corpus and dataset.

Acceptance checks:

- Evaluation results are stable and reproducible for the same corpus and dataset inputs.
- Reports make it clear when an extractor fails to process an item versus producing empty output.

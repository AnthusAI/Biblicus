# Roadmap

This document describes what we plan to build next.

If you are looking for runnable examples, see `docs/demos.md`.

If you are looking for what already exists, start with:

- `docs/feature-index.md` for a map of features to behavior specifications and modules.
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

- HMM analysis is reproducible for the same corpus state and extraction snapshot.
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

### Tactus integration

Tactus uses Biblicus as an ordinary Python dependency (`biblicus>=1.11.3,<2`). It shipped as library imports, not as a Model Context Protocol (MCP) toolset.

What Tactus uses:

- `biblicus.context_engine`: Tactus subclasses `ContextAssembler` and calls `retrieve_context_pack` to build context packs from evidence.
- `biblicus.context_engine.compaction`: Tactus builds its compactors from Biblicus.
- `biblicus.workflow`: Tactus calls `build_default_handler_registry`, `build_plan_for_extract`, and `build_plan_for_index` to plan extraction and indexing for a corpus.
- `biblicus.text` and `biblicus.ai.models`: the Tactus standard library wraps the text utilities and passes `LlmClientConfig`.
- `biblicus.corpus` and `biblicus.context`: `Corpus`, `ContextPack`, and `ContextPackBlock` cross the boundary as values.

Tactus is a consumer. Biblicus must keep these imports stable within a major version. A change that breaks one of them is a breaking change and needs a major version bump.

## Next: curation surface, consumer contract, and learned decisions

Papyrus, the automated newsroom, uses Biblicus for curation. It calls the `biblicus` command by subprocess. The next work makes that use first-class and moves learned decisions out of Biblicus.

### Curation surface on main

Goal: land the curation commands Papyrus already depends on, so that every command it calls exists on `main` and is specified.

Deliverables:

- These command groups, landed from their branches: taxonomy, steering, topic classifier, topic context and trends, summarize (map-reduce), article text, and block context packs.
- Behavior specifications and documentation for each command group.

Acceptance checks:

- Every command Papyrus calls runs from a released Biblicus, not from a branch.
- Each command group has end-to-end behavior specifications and full test coverage.

### Consumer contract for Papyrus

Goal: give Papyrus one stable, typed way to call Biblicus, with no guessing about paths or output shapes.

Deliverables:

- A `biblicus.api` module with a Pydantic request model and a Pydantic response model for each command Papyrus uses.
- `Corpus` methods that return the paths Papyrus needs (items, extraction snapshots, analysis outputs), so Papyrus never builds corpus paths by hand.
- Papyrus extension fields stored under `metadata.papyrus` on each item. Biblicus stores and returns them. It does not interpret them.
- Removal of the compatibility shims on both sides once the contract is in use.

Acceptance checks:

- Command output validates against the response models in `biblicus.api`.
- Papyrus reads corpus paths only through `Corpus` methods.
- No item metadata written by Papyrus lives outside `metadata.papyrus`.
- Neither project keeps a shim for the old call shapes.

### Learned decisions move to Cyclotron

Goal: stop learning human judgments inside Biblicus. Cyclotron (AnthusAI/Cyclotron) owns one recurring yes or no decision that learns from human review, such as whether a source is relevant or whether a proposal should be accepted.

Deliverables:

- Biblicus supplies features for each item: extracted text, item metadata, and topic signals.
- Cyclotron makes the decision and learns from reviews.
- Papyrus owns the reviewers, the review record, and the review interface.
- Relevance and proposal acceptance logic that learns from labels is removed from Biblicus.

Acceptance checks:

- Biblicus has no code that fits a model to human labels for relevance or proposal acceptance.
- The features Biblicus supplies are deterministic for the same corpus state and extraction snapshot.
- Documentation shows the hand-off: Biblicus produces features, Cyclotron decides, Papyrus reviews.

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

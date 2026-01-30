# Retrieval quality upgrades

This document describes the retrieval quality upgrades available in Biblicus. It is a reference for how retrieval
quality is expressed in runs and how to interpret the signals in artifacts and evidence.

## Goals

- Improve relevance without losing determinism or reproducibility.
- Keep retrieval stages explicit and visible in run artifacts.
- Preserve the evidence-first output model.

## Available upgrades

### 1) Tuned lexical baseline

- BM25-style scoring with configurable parameters.
- N-gram range controls.
- Stop word strategy per backend.
- Field weighting (for example: title, body, metadata).

### 2) Reranking stage

- Optional rerank step that re-scores top-N candidates.
- Deterministic scoring keeps rerank behavior reproducible.

### 3) Hybrid retrieval

- Combine lexical and embedding signals.
- Expose fusion weights in the recipe schema.
- Emit stage-level scores and weights in evidence metadata.

## Evaluation guidance

- Measure accuracy-at-k and compare against the same datasets.
- Run artifacts capture each stage and configuration for auditability.
- Deterministic settings remain available as the default baseline.

## Non-goals

- Automated hyperparameter tuning.
- Hidden fallback stages that obscure retrieval behavior.
- UI-driven tuning in this phase.

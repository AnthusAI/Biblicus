# Retrieval quality upgrades (planned)

This document records the design intent for planned retrieval quality upgrades. It is a reference for future work
and should be read alongside `docs/ROADMAP.md`.

## Goals

- Improve relevance without losing determinism or reproducibility.
- Keep retrieval stages explicit and visible in run artifacts.
- Preserve the evidence-first output model.

## Planned upgrades

### 1) Tuned lexical baseline

- BM25-style scoring with configurable parameters.
- N-gram range controls.
- Stop word strategy per backend.
- Field weighting (for example: title, body, metadata).

### 2) Reranking stage

- Optional rerank step that re-scores top-N candidates.
- Cross-encoder as the default deterministic path.
- Optional LLM reranking with structured outputs and explicit cost controls.

### 3) Hybrid retrieval

- Combine lexical and embedding signals.
- Expose fusion weights in the recipe schema.
- Emit stage-level scores and weights in evidence metadata.

## Evaluation requirements

- Accuracy-at-k improves on the same datasets without regressions.
- Run artifacts capture each stage and configuration for auditability.
- Deterministic settings remain available as the default baseline.

## Non-goals

- Automated hyperparameter tuning.
- Hidden fallback stages that obscure retrieval behavior.
- UI-driven tuning in this phase.

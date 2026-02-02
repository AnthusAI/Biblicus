# Retrieval quality upgrades

This document describes the retrieval quality upgrades available in Biblicus. It is a reference for how retrieval
quality is expressed in runs and how to interpret the signals in artifacts and evidence.

## Goals

- Improve relevance without losing determinism or reproducibility.
- Keep retrieval stages explicit and visible in run artifacts.
- Preserve the evidence-first output model.

## Available upgrades

### 1) Tuned lexical baseline

Biblicus exposes the knobs you use to shape lexical relevance without losing determinism:

- BM25-style scoring with configurable parameters.
- N-gram range controls.
- Stop word strategy per backend.
- Field weighting (for example: title, body, metadata).

Example configuration (SQLite full text search):

```
python -m biblicus build --corpus corpora/demo --backend sqlite-full-text-search \
  --config chunk_size=200 \
  --config chunk_overlap=50 \
  --config snippet_characters=120 \
  --config ngram_min=1 \
  --config ngram_max=2
```

### 2) Reranking stage

The optional rerank stage rescoring keeps retrieval quality transparent. It re-scores a bounded candidate set and
records rerank scores alongside retrieve scores in evidence metadata.

Example configuration:

```
python -m biblicus build --corpus corpora/demo --backend sqlite-full-text-search \
  --config rerank_enabled=true \
  --config rerank_model=cross-encoder \
  --config rerank_top_k=10
```

### 3) Hybrid retrieval

Hybrid retrieval combines lexical and vector signals. It expands candidate pools for each component backend, fuses
scores with explicit weights, and then applies the final budget.

Example configuration:

```
python -m biblicus build --corpus corpora/demo --backend hybrid \
  --config lexical_backend=sqlite-full-text-search \
  --config embedding_backend=vector \
  --config lexical_weight=0.7 \
  --config embedding_weight=0.3
```

Evidence items record both stage scores in `stage_scores` and preserve the hybrid weights in the run metadata so
evaluation can interpret how the fused ranking was produced.

## Evaluation guidance

Evaluation keeps the retrieval stages explicit and makes comparisons easy:

- Measure hit rate, precision-at-k, and mean reciprocal rank against shared datasets.
- Use the retrieval evaluation lab for a repeatable walkthrough (`scripts/retrieval_evaluation_lab.py`).
- Run artifacts capture each stage and configuration for auditability.
- Deterministic settings remain available as the default baseline.

## Interpreting evidence signals

Evidence returned by retrieval runs includes a `stage` label and optional `stage_scores` map:

- `stage` identifies the last stage that produced the evidence (for example, `retrieve`, `rerank`, `hybrid`).
- `stage_scores` contains per-stage scores so you can compare lexical and vector contributions in hybrid runs.

Use these fields to understand how a candidate moved through the pipeline and why it ranked where it did.

## Budget awareness

Budgets shape every retrieval comparison:

- `max_total_items` limits the evidence list length and defines the denominator for precision-at-k.
- `maximum_total_characters` controls how much text can survive into evidence outputs.
- `max_items_per_source` prevents one source from dominating the final list.

When you compare backends, keep budgets constant and note any candidate expansion in hybrid runs so fused rankings are
drawn from comparable pools.

## Evidence tracing checklist

- Inspect `stage` and `stage_scores` to see where ranking changes occurred.
- Compare `score` against `stage_scores` to understand fusion effects.
- Use `recipe_id` and `run_id` to map evidence back to run manifests.

## Non-goals

- Automated hyperparameter tuning.
- Hidden fallback stages that obscure retrieval behavior.
- UI-driven tuning in this phase.

## Summary

Retrieval quality upgrades in Biblicus keep determinism intact while making scoring richer and more interpretable.
Start with tuned lexical baselines, add reranking when you need sharper relevance, and reach for hybrid retrieval when
you want to balance lexical precision with semantic similarity signals. Evaluate each change with the same dataset and
budget so improvements remain credible and reproducible.

# Retrieval

Biblicus treats retrieval as a reproducible, explicit pipeline stage that transforms a corpus into structured evidence.
Retrieval is separated from extraction and context shaping so each can be evaluated independently and swapped without
rewriting ingestion.

## Retrieval concepts

- **Backend**: a pluggable retrieval implementation that can build and query runs.
- **Run**: a recorded retrieval build for a corpus and extraction run.
- **Evidence**: structured output containing identifiers, provenance, and scores.
- **Stage**: explicit steps such as retrieve, rerank, and filter.

## How retrieval runs work

1) Ingest raw items into a corpus.
2) Build an extraction run to produce text artifacts.
3) Build a retrieval run with a backend, referencing the extraction run.
4) Query the run to return evidence.

Retrieval runs are stored under:

```
.biblicus/runs/retrieval/<backend_id>/<run_id>/
```

## Backends

See `docs/backends/index.md` for backend selection and configuration.

## Evaluation

Retrieval runs are evaluated against datasets with explicit budgets. See `docs/RETRIEVAL_EVALUATION.md` for the
dataset format and workflow, `docs/FEATURE_INDEX.md` for the behavior specifications, and `docs/CONTEXT_PACK.md` for
how evidence feeds into context packs.

## Why the separation matters

Keeping extraction and retrieval distinct makes it possible to:

- Reuse the same extracted artifacts across many retrieval backends.
- Compare backends against the same corpus and dataset inputs.
- Record and audit retrieval decisions without mixing in prompting or context formatting.

## Retrieval quality

For retrieval quality upgrades, see `docs/RETRIEVAL_QUALITY.md`.

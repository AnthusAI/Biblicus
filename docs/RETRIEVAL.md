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

## A minimal run you can execute

This walkthrough uses the full text search backend and produces evidence you can inspect immediately.

```
rm -rf corpora/retrieval_demo
python -m biblicus init corpora/retrieval_demo
printf "alpha beta\n" > /tmp/retrieval-alpha.txt
printf "beta gamma\n" > /tmp/retrieval-beta.txt
python -m biblicus ingest --corpus corpora/retrieval_demo /tmp/retrieval-alpha.txt
python -m biblicus ingest --corpus corpora/retrieval_demo /tmp/retrieval-beta.txt

python -m biblicus extract build --corpus corpora/retrieval_demo --step pass-through-text
python -m biblicus build --corpus corpora/retrieval_demo --backend sqlite-full-text-search
python -m biblicus query --corpus corpora/retrieval_demo --query "beta"
```

The query output is structured evidence with identifiers and scores. That evidence is the primary output for evaluation
and downstream context packing.

## Backends

See `docs/backends/index.md` for backend selection and configuration.

## Choosing a backend

Start with the simplest backend that answers your question:

- `scan` for tiny corpora or sanity checks.
- `sqlite-full-text-search` for a practical lexical baseline.
- `tf-vector` when you want deterministic term-frequency similarity without external dependencies.
- `embedding-index-file` when you want embedding retrieval with a local, file-backed index.

You can compare them with the same dataset and budget using the retrieval evaluation workflow.

## Evaluation

Retrieval runs are evaluated against datasets with explicit budgets. See `docs/RETRIEVAL_EVALUATION.md` for the
dataset format and workflow, `docs/FEATURE_INDEX.md` for the behavior specifications, and `docs/CONTEXT_PACK.md` for
how evidence feeds into context packs.

## Evidence inspection workflow

When you want to understand a result end to end:

1) Query the backend and save the output.
2) Inspect the top evidence items and their scores.
3) Trace each evidence `item_id` back to the corpus for context.

Example:

```
python -m biblicus query --corpus corpora/demo --query "beta" > /tmp/retrieval_output.json
python -c "import json; data=json.load(open('/tmp/retrieval_output.json')); print(data['evidence'][:2])"
python -m biblicus show --corpus corpora/demo ITEM_ID
```

## Saving evidence for later analysis

Evidence output is stable JSON. Save it alongside your experiments so you can compare runs later:

```
python -m biblicus query --corpus corpora/demo --query "beta" > artifacts/retrieval/beta.json
```

Record the run identifier and budget values in the same folder so you can reproduce the query.

## Labs and demos

When you want a repeatable example with bundled data, use the retrieval evaluation lab:

```
python scripts/retrieval_evaluation_lab.py --corpus corpora/retrieval_eval_lab --force
```

The lab builds a tiny corpus, runs extraction, builds a retrieval run, and evaluates it. It prints the dataset path and
evaluation output so you can open the JavaScript Object Notation directly.

## Reproducibility checklist

Use these habits when you want repeatable retrieval experiments:

- Record the extraction run identifier and pass it explicitly when you build a retrieval run.
- Keep evaluation datasets in source control and treat them as immutable inputs.
- Capture the full retrieval run identifier when you compare outputs across backends.

## Why the separation matters

Keeping extraction and retrieval distinct makes it possible to:

- Reuse the same extracted artifacts across many retrieval backends.
- Compare backends against the same corpus and dataset inputs.
- Record and audit retrieval decisions without mixing in prompting or context formatting.

## Retrieval quality

For retrieval quality upgrades, see `docs/RETRIEVAL_QUALITY.md`.

# Retrieval evaluation

Biblicus evaluates retrieval runs against deterministic datasets so quality comparisons are repeatable across backends
and corpora. Evaluations keep the evidence-first model intact by reporting per-query evidence alongside summary
metrics.

## Dataset format

Retrieval datasets are stored as JavaScript Object Notation files with a strict schema:

```json
{
  "schema_version": 1,
  "name": "example-dataset",
  "description": "Small hand-labeled dataset for smoke tests.",
  "queries": [
    {
      "query_id": "q-001",
      "query_text": "alpha",
      "expected_item_id": "item-id-123",
      "kind": "gold"
    }
  ]
}
```

Each query includes either an `expected_item_id` or an `expected_source_uri`. The `kind` field records whether the
query is hand-labeled (`gold`) or synthetic.

## Metrics primer

Retrieval evaluation reports a small set of textbook metrics:

- **Hit rate**: the fraction of queries that retrieved the expected item at any rank.
- **Precision-at-k**: hit rate normalized by the evidence budget (`max_total_items`).
- **Mean reciprocal rank**: the average of `1 / rank` for the first matching item per query.

These metrics are deterministic for the same corpus, run, dataset, and budget.

## Running an evaluation

Use the command-line interface to evaluate a retrieval run against a dataset:

```bash
biblicus eval --corpus corpora/example --run <run_id> --dataset datasets/retrieval.json \
  --max-total-items 5 --maximum-total-characters 2000 --max-items-per-source 5
```

If `--run` is omitted, the latest retrieval run is used. Evaluations are deterministic for the same corpus, run, and
budget.

## End-to-end evaluation example

This example builds a tiny corpus, creates a retrieval run, and evaluates it against a minimal dataset:

```
rm -rf corpora/retrieval_eval_demo
python -m biblicus init corpora/retrieval_eval_demo
printf "alpha apple\n" > /tmp/eval-alpha.txt
printf "beta banana\n" > /tmp/eval-beta.txt
python -m biblicus ingest --corpus corpora/retrieval_eval_demo /tmp/eval-alpha.txt
python -m biblicus ingest --corpus corpora/retrieval_eval_demo /tmp/eval-beta.txt

python -m biblicus extract build --corpus corpora/retrieval_eval_demo --step pass-through-text
python -m biblicus build --corpus corpora/retrieval_eval_demo --backend sqlite-full-text-search

cat > /tmp/retrieval_eval_dataset.json <<'JSON'
{
  "schema_version": 1,
  "name": "retrieval-eval-demo",
  "description": "Minimal dataset for evaluation walkthroughs.",
  "queries": [
    {
      "query_id": "q1",
      "query_text": "apple",
      "expected_item_id": "ITEM_ID_FOR_ALPHA",
      "kind": "gold"
    }
  ]
}
JSON
```

Replace `ITEM_ID_FOR_ALPHA` with the item identifier from `biblicus list`, then run:

```
python -m biblicus eval --corpus corpora/retrieval_eval_demo --dataset /tmp/retrieval_eval_dataset.json \
  --max-total-items 3 --maximum-total-characters 2000 --max-items-per-source 5
```

## Authoring a dataset from a corpus

Use this workflow when you want to build a small, hand-labeled dataset:

1) Ingest a small, representative subset of items.
2) Run extraction and build a retrieval run.
3) Use `biblicus list` to capture item identifiers.
4) Write a dataset JSON that maps queries to `expected_item_id` values.

Example skeleton:

```json
{
  "schema_version": 1,
  "name": "my-retrieval-dataset",
  "description": "Hand-labeled queries for evaluation.",
  "queries": [
    {
      "query_id": "q1",
      "query_text": "example query",
      "expected_item_id": "ITEM_ID",
      "kind": "gold"
    }
  ]
}
```

## Retrieval evaluation lab

The retrieval evaluation lab ships with bundled files and labels so you can run a deterministic end-to-end evaluation
without external dependencies.

```
python scripts/retrieval_evaluation_lab.py --corpus corpora/retrieval_eval_lab --force
```

The script prints a summary that includes the generated dataset path, the retrieval run identifier, and the evaluation
output path.

## Output

The evaluation output includes:

- Dataset metadata (name, description, query count).
- Run metadata (backend ID, run ID, evaluation timestamp).
- Metrics (hit rate, precision-at-k, mean reciprocal rank).
- System diagnostics (latency percentiles and index size).

The output is JavaScript Object Notation suitable for downstream reporting.

Example snippet:

```json
{
  "dataset": {
    "name": "retrieval-eval-demo",
    "description": "Minimal dataset for evaluation walkthroughs.",
    "queries": 1
  },
  "backend_id": "sqlite-full-text-search",
  "run_id": "RUN_ID",
  "evaluated_at": "2024-01-01T00:00:00Z",
  "metrics": {
    "hit_rate": 1.0,
    "precision_at_max_total_items": 0.3333333333333333,
    "mean_reciprocal_rank": 1.0
  },
  "system": {
    "average_latency_milliseconds": 1.2,
    "percentile_95_latency_milliseconds": 2.4,
    "index_bytes": 2048.0
  }
}
```

The `metrics` section is the primary signal for retriever quality. The `system` section helps compare performance and
storage costs across backends.

## Reading per-query diagnostics

When a query misses, inspect the evidence list for that query and compare it to your expectations:

- Is the expected item present but ranked too low?
- Is the expected item missing because extraction did not produce text?
- Did the budget truncate the relevant evidence?

Use this inspection to decide whether to adjust extraction, retrieval configuration, or evaluation datasets.

## What to record for comparisons

When you compare retrieval runs, capture the same inputs every time:

- Corpus path (and whether the catalog has been reindexed).
- Extraction run identifier used by the retrieval run.
- Retrieval backend identifier and run identifier.
- Evaluation dataset path and schema version.
- Evidence budget values.

This metadata allows you to rerun the evaluation and explain differences between results.

## Common pitfalls

- Evaluating against a dataset built for a different corpus or extraction run.
- Changing budgets between runs and expecting metrics to be comparable.
- Using stale item identifiers after reindexing or re-ingesting content.

## Python usage

```python
from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.evaluation import evaluate_run, load_dataset
from biblicus.models import QueryBudget

corpus = Corpus.open("corpora/example")
run = corpus.load_run("<run_id>")
dataset = load_dataset(Path("datasets/retrieval.json"))
budget = QueryBudget(max_total_items=5, maximum_total_characters=2000, max_items_per_source=5)
result = evaluate_run(corpus=corpus, run=run, dataset=dataset, budget=budget)
print(result.model_dump_json(indent=2))
```

## Design notes

- Evaluation is reproducible by construction: the run manifest, dataset, and budget fully determine the results.
- The evaluation workflow expects retrieval stages to remain explicit in the run artifacts.
- Reports are portable, so comparisons across backends and corpora are straightforward.

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

## Running an evaluation

Use the command-line interface to evaluate a retrieval run against a dataset:

```bash
biblicus eval --corpus corpora/example --run <run_id> --dataset datasets/retrieval.json \
  --max-total-items 5 --max-total-characters 2000 --max-items-per-source 5
```

If `--run` is omitted, the latest retrieval run is used. Evaluations are deterministic for the same corpus, run, and
budget.

## Output

The evaluation output includes:

- Dataset metadata (name, description, query count).
- Run metadata (backend ID, run ID, evaluation timestamp).
- Metrics (hit rate, precision-at-k, mean reciprocal rank).
- System diagnostics (latency percentiles and index size).

The output is JavaScript Object Notation suitable for downstream reporting.

## Python usage

```python
from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.evaluation import evaluate_run, load_dataset
from biblicus.models import QueryBudget

corpus = Corpus.open("corpora/example")
run = corpus.load_run("<run_id>")
dataset = load_dataset(Path("datasets/retrieval.json"))
budget = QueryBudget(max_total_items=5, max_total_characters=2000, max_items_per_source=5)
result = evaluate_run(corpus=corpus, run=run, dataset=dataset, budget=budget)
print(result.model_dump_json(indent=2))
```

## Design notes

- Evaluation is reproducible by construction: the run manifest, dataset, and budget fully determine the results.
- The evaluation workflow expects retrieval stages to remain explicit in the run artifacts.
- Reports are portable, so comparisons across backends and corpora are straightforward.

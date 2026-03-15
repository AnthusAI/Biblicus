# Extraction evaluation

Biblicus provides an extraction evaluation harness that measures how well an extractor configuration turns raw items into text.
It is designed to be deterministic, auditable, and useful for selecting a default extraction pipeline.

## What extraction evaluation measures

Extraction evaluation reports:

- Coverage of extracted text (present, empty, missing)
- Accuracy against labeled ground truth text
- Processable fraction for each extractor configuration
- Optional system metrics such as latency and external cost

The output is structured JSON so you can version it, compare it across runs, and use it in reports.

## Dataset format

Extraction evaluation datasets are JSON with a versioned schema. Each entry maps a corpus item to its expected extracted
text.

Example:

```json
{
  "schema_version": 1,
  "name": "Extraction baseline",
  "description": "Short labeled texts for extraction accuracy",
  "items": [
    {
      "item_id": "3a2c3f0b-...",
      "expected_text": "Hello world",
      "kind": "gold"
    },
    {
      "source_uri": "file:///corpora/demo/report.pdf",
      "expected_text": "Quarterly results",
      "kind": "gold"
    }
  ]
}
```

Fields:

- `schema_version`: dataset schema version, currently `1`
- `name`: dataset name
- `description`: optional description
- `items`: list of labeled items with either `item_id` or `source_uri`
- `expected_text`: expected extracted text for the item
- `kind`: label kind, for example `gold` or `synthetic`

## Run extraction evaluation from the CLI

```
biblicus extract evaluate --corpus corpora/example \
  --run pipeline:EXTRACTION_SNAPSHOT_ID \
  --dataset datasets/extraction.json
```

If you omit `--run`, Biblicus uses the latest extraction snapshot and emits a reproducibility warning.

## Run extraction evaluation from Python

```
from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.extraction_evaluation import evaluate_extraction_snapshot, load_extraction_dataset
from biblicus.models import ExtractionRunReference

corpus = Corpus.open(Path("corpora/example"))
run = corpus.load_extraction_snapshot("pipeline", "RUN_ID")
dataset = load_extraction_dataset(Path("datasets/extraction.json"))
result = evaluate_extraction_snapshot(corpus=corpus, run=run, dataset=dataset)
print(result.model_dump())
```

## Output location

Extraction evaluation artifacts are stored under:

```
analysis/evaluation/extraction/<snapshot_id>/output.json
```

## Reading the output

Evaluation outputs include metrics and dataset/run metadata. A shortened example:

```json
{
  "dataset": {
    "name": "Extraction baseline",
    "description": "Short labeled texts for extraction accuracy",
    "items": 2
  },
  "snapshot_id": "pipeline:RUN_ID",
  "metrics": {
    "coverage_present": 2.0,
    "coverage_empty": 0.0,
    "coverage_missing": 0.0,
    "processable_fraction": 1.0,
    "average_similarity": 1.0
  }
}
```

Use `coverage_*` to understand how much text was produced and `average_similarity` to compare extraction quality.

## Working demo

A runnable demo is provided in `scripts/extraction_evaluation_demo.py`. It downloads AG News, runs extraction, builds a
dataset from the ingested items, and evaluates the extraction snapshot:

```
python scripts/extraction_evaluation_demo.py --corpus corpora/ag_news_extraction_eval --force
```

## Extraction evaluation lab

For a fast, fully local walkthrough, use the bundled lab. It ingests a tiny set of files, runs extraction, generates a
dataset, and evaluates the run in seconds.

```
python scripts/extraction_evaluation_lab.py --corpus corpora/extraction_eval_lab --force
```

The lab uses the bundled files under `datasets/extraction_lab/items` and writes the generated dataset to
`datasets/extraction_lab_output.json` by default. The command output includes the evaluation artifact path so you can
inspect the metrics immediately.

### Lab walkthrough

1) Run the lab:

```
python scripts/extraction_evaluation_lab.py --corpus corpora/extraction_eval_lab --force
```

2) Inspect the generated dataset:

```
cat datasets/extraction_lab_output.json
```

The dataset is small and deterministic. Each entry maps a corpus item to the expected extracted text.

3) Inspect the evaluation output:

```
cat corpora/extraction_eval_lab/analysis/evaluation/extraction/<snapshot_id>/output.json
```

The output includes:

- Coverage counts for present, empty, and missing extracted text.
- Processable fraction for the extractor configuration.
- Average similarity between expected and extracted text.

4) Compare metrics to raw items:

The lab includes a Markdown note, a plain text file, and a blank Markdown note. The blank note yields empty extracted
text, which should be reflected in the coverage metrics. Because the expected text matches the extracted text for the
non-empty items, the similarity score is 1.0 for those items.

## Interpretation tips

- Use coverage metrics to detect extractors that skip or fail on specific media types.
- Use accuracy metrics to compare competing extractors on labeled samples.
- Track processable fraction before optimizing quality so you know what fraction of the corpus is actually evaluated.

## Common pitfalls

- Evaluating a run with a dataset built from a different corpus.
- Forgetting to record the extraction snapshot reference in experiment logs.
- Comparing runs with different label sets or dataset sizes.

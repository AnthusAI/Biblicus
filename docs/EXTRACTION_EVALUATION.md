# Extraction evaluation

Biblicus provides an extraction evaluation harness that measures how well an extractor recipe turns raw items into text.
It is designed to be deterministic, auditable, and useful for selecting a default extraction pipeline.

## What extraction evaluation measures

Extraction evaluation reports:

- Coverage of extracted text (present, empty, missing)
- Accuracy against labeled ground truth text
- Processable fraction for each extractor recipe
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
  --run pipeline:EXTRACTION_RUN_ID \
  --dataset datasets/extraction.json
```

If you omit `--run`, Biblicus uses the latest extraction run and emits a reproducibility warning.

## Run extraction evaluation from Python

```
from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.extraction_evaluation import evaluate_extraction_run, load_extraction_dataset
from biblicus.models import ExtractionRunReference

corpus = Corpus.open(Path("corpora/example"))
run = corpus.load_extraction_run("pipeline", "RUN_ID")
dataset = load_extraction_dataset(Path("datasets/extraction.json"))
result = evaluate_extraction_run(corpus=corpus, run=run, dataset=dataset)
print(result.model_dump())
```

## Output location

Extraction evaluation artifacts are stored under:

```
.biblicus/runs/evaluation/extraction/<run_id>/output.json
```

## Working demo

A runnable demo is provided in `scripts/extraction_evaluation_demo.py`. It downloads AG News, runs extraction, builds a
dataset from the ingested items, and evaluates the extraction run:

```
python3 scripts/extraction_evaluation_demo.py --corpus corpora/ag_news_extraction_eval --force
```

## Interpretation tips

- Use coverage metrics to detect extractors that skip or fail on specific media types.
- Use accuracy metrics to compare competing extractors on labeled samples.
- Track processable fraction before optimizing quality so you know what fraction of the corpus is actually evaluated.

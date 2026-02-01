# Corpus profiling analysis

Biblicus provides a profiling analysis backend that summarizes corpus contents using deterministic counts and
coverage metrics. Profiling is intended as a fast, local baseline before heavier analysis such as topic modeling.

## What profiling does

The profiling analysis reports:

- Total item count and media type distribution
- Extracted text coverage (present, empty, missing)
- Size and length distributions with percentiles
- Tag coverage and top tags

The output is structured JSON that can be stored, versioned, and compared across runs.

## Run profiling from the CLI

```
biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

If you omit `--extraction-run`, Biblicus uses the latest extraction run and emits a reproducibility warning.

To customize profiling metrics, pass a recipe file:

```
biblicus analyze profile --corpus corpora/example --recipe recipes/profiling.yml --extraction-run pipeline:RUN_ID
```

Profiling recipes support cascading composition. Pass multiple `--recipe` files; later recipes override earlier recipes
via a deep merge:

```
biblicus analyze profile \
  --corpus corpora/example \
  --recipe recipes/profiling/base.yml \
  --recipe recipes/profiling/strict.yml \
  --extraction-run pipeline:RUN_ID
```

To override the composed configuration view from the command line, use `--config key=value` with dotted keys:

```
biblicus analyze profile \
  --corpus corpora/example \
  --recipe recipes/profiling/base.yml \
  --config sample_size=200 \
  --extraction-run pipeline:RUN_ID
```

### Profiling recipe configuration

Profiling recipes use the analysis schema version and accept these fields:

- `schema_version`: analysis schema version, currently `1`
- `sample_size`: optional cap for distribution calculations
- `min_text_characters`: minimum extracted text length for inclusion
- `percentiles`: percentiles to compute for size and length distributions
- `top_tag_count`: maximum number of tags to list in `top_tags`
- `tag_filters`: optional list of tags to include in tag coverage metrics

Example recipe:

```
schema_version: 1
sample_size: 500
min_text_characters: 50
percentiles: [50, 90, 99]
top_tag_count: 10
tag_filters: ["ag_news", "label:World"]
```

## Run profiling from Python

```
from pathlib import Path

from biblicus.analysis import get_analysis_backend
from biblicus.corpus import Corpus
from biblicus.models import ExtractionRunReference

corpus = Corpus.open(Path("corpora/example"))
backend = get_analysis_backend("profiling")
output = backend.run_analysis(
    corpus,
    recipe_name="default",
    config={
        "schema_version": 1,
        "sample_size": 500,
        "min_text_characters": 50,
        "percentiles": [50, 90, 99],
        "top_tag_count": 10,
        "tag_filters": ["ag_news"],
    },
    extraction_run=ExtractionRunReference(
        extractor_id="pipeline",
        run_id="RUN_ID",
    ),
)
print(output.model_dump())
```

## Output location

Profiling output is stored under:

```
.biblicus/runs/analysis/profiling/<run_id>/output.json
```

## Reading the report

Profiling output is a structured report with separate sections for raw items and extracted text. A shortened example:

```json
{
  "analysis_id": "profiling",
  "generated_at": "2024-01-01T00:00:00Z",
  "report": {
    "raw_items": {
      "total_items": 3,
      "media_type_counts": {
        "text/markdown": 3
      }
    },
    "extracted_text": {
      "extracted_nonempty_items": 3,
      "extracted_empty_items": 0,
      "extracted_missing_items": 0
    }
  }
}
```

The `raw_items` section summarizes corpus composition. The `extracted_text` section tells you how much content made it
through extraction and how much was missing or empty.

## Comparing profiling runs

Use the same extraction run and recipe configuration whenever you compare profiling outputs:

1) Run profiling on two corpus snapshots.
2) Compare `raw_items.total_items`, media type counts, and tag coverage.
3) Compare `extracted_text` coverage to spot extraction regressions.

Record the run identifiers and catalog timestamps so you can trace differences later.

## Common pitfalls

- Profiling without specifying an extraction run, which makes comparisons harder to reproduce.
- Comparing runs with different `sample_size` or `min_text_characters` settings.
- Interpreting tag counts without noting the `tag_filters` applied.

## Working demo

A runnable demo is provided in `scripts/profiling_demo.py`. It downloads a corpus, runs extraction, and executes the
profiling analysis so you can inspect the output:

```
python scripts/profiling_demo.py --corpus corpora/profiling_demo --force
```

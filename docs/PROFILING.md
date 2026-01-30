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

## Working demo

A runnable demo is provided in `scripts/profiling_demo.py`. It downloads a corpus, runs extraction, and executes the
profiling analysis so you can inspect the output:

```
python3 scripts/profiling_demo.py --corpus corpora/profiling_demo --force
```

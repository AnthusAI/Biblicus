# Corpus analysis

Biblicus supports analysis backends that run on extracted text artifacts without changing the raw corpus. Analysis is a
pluggable phase that reads an extraction run, produces structured output, and stores artifacts under the corpus runs
folder. Each analysis backend declares its own configuration schema and output contract, and all schemas are validated
strictly.

## How analysis runs work

- Analysis runs are tied to a corpus state via the extraction run reference.
- The analysis output is written under `.biblicus/runs/analysis/<analysis-id>/<run_id>/`.
- Analysis is reproducible when you supply the same extraction run and corpus catalog state.
- Analysis configuration is stored as a recipe manifest in the run metadata.

If you omit the extraction run, Biblicus uses the most recent extraction run and emits a reproducibility warning. For
repeatable analysis runs, always pass the extraction run reference explicitly.

## Analysis run artifacts

Every analysis run records a manifest alongside the output:

```
.biblicus/runs/analysis/<analysis-id>/<run_id>/
  manifest.json
  output.json
```

The manifest captures the recipe, extraction run reference, and catalog timestamp so results can be reproduced and
compared later.

## Inspecting output

Analysis outputs are JSON documents. You can view them directly:

```
cat corpora/example/.biblicus/runs/analysis/profiling/RUN_ID/output.json
```

Each analysis backend defines its own `report` payload. The run metadata is consistent across backends.

## Comparing analysis runs

When you compare analysis results, record:

- Corpus path and catalog timestamp.
- Extraction run reference.
- Analysis recipe name and configuration.
- Analysis run identifier and output path.

These make it possible to rerun the analysis and explain differences.

## Pluggable analysis backends

Analysis backends implement the `CorpusAnalysisBackend` interface and are registered under `biblicus.analysis`.
A backend receives the corpus, a recipe name, a configuration mapping, and an extraction run reference. It returns a
Pydantic model that is serialized to JavaScript Object Notation for storage.

## Recipe files

Analysis recipes are optional JavaScript Object Notation or YAML files that capture configuration in a repeatable way.
They are useful for sharing experiments and keeping runs reproducible.

Minimal profiling recipe:

```
schema_version: 1
```

Minimal topic modeling recipe:

```
schema_version: 1
text_source:
  sample_size: 500
bertopic_analysis:
  parameters:
    nr_topics: 8
```

## Topic modeling

Topic modeling is the first analysis backend. It uses BERTopic to cluster extracted text, produces per-topic evidence,
and optionally labels topics using an LLM. See `docs/TOPIC_MODELING.md` for detailed configuration and examples.

The integration demo script is a working reference you can use as a starting point:

```
python3 scripts/topic_modeling_integration.py --corpus corpora/ag_news_demo --force
```

The command prints the analysis run identifier and the output path. Open the resulting `output.json` to inspect per-topic
labels, keywords, and document examples.

## Profiling analysis

Profiling is the baseline analysis backend. It summarizes corpus composition and extraction coverage using
deterministic counts and distribution metrics. See `docs/PROFILING.md` for the full reference and working demo.

### Minimal profiling run

```
python3 -m biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

The command writes an analysis run directory and prints the run identifier.

Run profiling from the CLI:

```
biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

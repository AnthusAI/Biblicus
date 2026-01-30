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

## Pluggable analysis backends

Analysis backends implement the `CorpusAnalysisBackend` interface and are registered under `biblicus.analysis`.
A backend receives the corpus, a recipe name, a configuration mapping, and an extraction run reference. It returns a
Pydantic model that is serialized to JavaScript Object Notation for storage.

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

Run profiling from the CLI:

```
biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

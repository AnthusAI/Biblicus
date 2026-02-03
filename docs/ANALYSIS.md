# Corpus analysis

Biblicus supports analysis backends that run on extracted text artifacts without changing the raw corpus. Analysis is a
pluggable phase that reads an extraction snapshot, produces structured output, and stores artifacts under the corpus runs
folder. Each analysis backend declares its own configuration schema and output contract, and all schemas are validated
strictly.

## How analysis snapshots work

- Analysis runs are tied to a corpus state via the extraction snapshot reference.
- The analysis output is written under `.biblicus/runs/analysis/<analysis-id>/<snapshot_id>/`.
- Analysis is reproducible when you supply the same extraction snapshot and corpus catalog state.
- Analysis configuration is stored as a configuration manifest in the run metadata.

If you omit the extraction snapshot, Biblicus uses the most recent extraction snapshot and emits a reproducibility warning. For
repeatable analysis snapshots, always pass the extraction snapshot reference explicitly.

## Analysis snapshot artifacts

Every analysis snapshot records a manifest alongside the output:

```
.biblicus/runs/analysis/<analysis-id>/<snapshot_id>/
  manifest.json
  output.json
```

The manifest captures the configuration, extraction snapshot reference, and catalog timestamp so results can be reproduced and
compared later.

## Inspecting output

Analysis outputs are JSON documents. You can view them directly:

```
cat corpora/example/.biblicus/runs/analysis/profiling/RUN_ID/output.json
```

Each analysis backend defines its own `report` payload. The run metadata is consistent across backends.

## Comparing analysis snapshots

When you compare analysis results, record:

- Corpus path and catalog timestamp.
- Extraction run reference.
- Analysis configuration name and configuration.
- Analysis snapshot identifier and output path.

These make it possible to rerun the analysis and explain differences.

## Pluggable analysis backends

Analysis backends implement the `CorpusAnalysisBackend` interface and are registered under `biblicus.analysis`.
A backend receives the corpus, a configuration name, a configuration mapping, and an extraction snapshot reference. It returns a
Pydantic model that is serialized to JavaScript Object Notation for storage.

## Choosing an analysis backend

Start with profiling when you need fast, deterministic baselines. Use topic modeling when you want thematic clustering
and exploratory labels. Use Markov analysis when you want state-transition structure over sequences of segments.
Combine multiple backends for a clear view of corpus composition, themes, and state dynamics.

## Configuration files

Analysis configurations are optional JavaScript Object Notation or YAML files that capture configuration in a repeatable way.
They are useful for sharing experiments and keeping runs reproducible.

Recipes support cascading composition. When a command accepts `--configuration`, you can pass multiple configuration files. Biblicus
merges them in order, where later configurations override earlier configurations via a deep merge. You can then apply `--config`
overrides on top of the composed view.

Minimal profiling configuration:

```
schema_version: 1
```

Minimal topic modeling configuration:

```
schema_version: 1
text_source:
  sample_size: 500
bertopic_analysis:
  parameters:
    nr_topics: 8
```

Minimal Markov analysis configuration:

```
schema_version: 1
model:
  family: gaussian
  n_states: 8
segmentation:
  method: sentence
observations:
  encoder: tfidf
```

## Topic modeling

Topic modeling is the first analysis backend. It uses BERTopic to cluster extracted text, produces per-topic evidence,
and optionally labels topics using an LLM. See `docs/TOPIC_MODELING.md` for detailed configuration and examples.

The integration demo script is a working reference you can use as a starting point:

```
python scripts/topic_modeling_integration.py --corpus corpora/ag_news_demo --force
```

The command prints the analysis snapshot identifier and the output path. Open the resulting `output.json` to inspect per-topic
labels, keywords, and document examples.

## Markov analysis

Markov analysis learns a directed, weighted state transition graph over sequences of text segments. The output includes
per-state exemplars, per-item decoded paths, and optional GraphViz exports. See `docs/MARKOV_ANALYSIS.md` for detailed
configuration and examples.

Text extract is available as a segmentation strategy for long texts. It inserts XML tags in-place using a virtual file
editing loop, then extracts spans without requiring the model to re-emit the full transcript.

## Profiling analysis

Profiling is the baseline analysis backend. It summarizes corpus composition and extraction coverage using
deterministic counts and distribution metrics. See `docs/PROFILING.md` for the full reference and working demo.

### Minimal profiling run

```
python -m biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

The command writes an analysis snapshot directory and prints the snapshot identifier.

Run profiling from the CLI:

```
biblicus analyze profile --corpus corpora/example --extraction-run pipeline:RUN_ID
```

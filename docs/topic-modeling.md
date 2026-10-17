# Topic modeling

Biblicus provides a topic modeling analysis backend that reads extracted text artifacts, optionally applies an LLM
extraction pass, optionally removes named entities, applies lexical processing, and runs BERTopic. Topic labels are
refined through BERTopic representation models when configured. The output is structured JavaScript Object Notation
with explicit per-topic evidence.

## What topic modeling does

Topic modeling groups documents into clusters based on shared terms or phrases, then surfaces representative
keywords for each cluster. It is a fast way to summarize large corpora, identify dominant themes, and spot outliers
without manual labeling. The output is not a classifier; it is an exploratory tool that produces evidence that can
be inspected or reviewed by humans.

## About BERTopic

BERTopic combines document embeddings with clustering and a class-based term frequency approach to extract topic
keywords. Biblicus supports BERTopic as an optional dependency and forwards its configuration parameters directly to
the BERTopic constructor. This allows you to tune clustering behavior while keeping the output in a consistent
schema.

## Pipeline stages

- Text collection reads extracted text artifacts from an extraction snapshot.
- LLM extraction optionally transforms each document into one or more analysis documents.
- Entity removal optionally deletes named entities before modeling.
- Lexical processing optionally normalizes text before BERTopic.
- BERTopic produces topic assignments, keyword weights, and representation-model labels when configured.

## Run topic modeling from the CLI

```
biblicus analyze topics --corpus corpora/example --configuration configurations/topic-modeling.yml --extraction-snapshot pipeline:RUN_ID
```

Topic modeling configurations support cascading composition. Pass multiple `--configuration` files; later configurations override earlier
configurations via a deep merge:

```
biblicus analyze topics \
  --corpus corpora/example \
  --configuration configurations/topic-modeling/base.yml \
  --configuration configurations/topic-modeling/ag-news.yml \
  --extraction-snapshot pipeline:RUN_ID
```

To override the composed configuration view from the command line, use `--config key=value` with dotted keys:

```
biblicus analyze topics \
  --corpus corpora/example \
  --configuration configurations/topic-modeling/base.yml \
  --configuration configurations/topic-modeling/ag-news.yml \
  --config bertopic_analysis.parameters.nr_topics=12 \
  --extraction-snapshot pipeline:RUN_ID
```

If you omit `--extraction-snapshot`, Biblicus uses the latest extraction snapshot and emits a reproducibility warning.

## Output structure

Topic modeling writes a single `output.json` file under the analysis snapshot directory. The output contains:

- `run.snapshot_id` and `run.stats` for reproducible tracking.
- `report.topics` with the modeled topics.
- `report.text_collection`, `report.llm_extraction`, `report.entity_removal`, `report.lexical_processing`,
  `report.bertopic_analysis`, and `report.representation_model` describing each pipeline stage.

When entity removal is enabled, Biblicus also writes `entity_removal.jsonl` alongside `output.json`. This artifact
contains the redacted documents that feed BERTopic and is reused on subsequent runs for the same snapshot.

Each topic record includes:

- `topic_id`: The BERTopic topic identifier. The outlier topic uses `-1`.
- `label`: The human-readable label.
- `label_source`: `bertopic` or `llm` depending on whether BERTopic keyword representation or a BERTopic
  representation model set the label.
- `keywords`: Keyword list with weights.
- `document_count`: Number of documents assigned to the topic.
- `document_ids`: Item identifiers for the assigned documents.
- `document_examples`: Sampled document text used for inspection.

Per-topic behavior is determined by the BERTopic assignments and optional BERTopic representation model. The lexical
processing flags can substantially change tokenization and therefore the resulting topic labels. The outlier
`topic_id` `-1` indicates documents that BERTopic could not confidently assign to a cluster.

### Reading a topic record

Each topic includes evidence you can inspect. A shortened example:

```json
{
  "topic_id": 2,
  "label": "global markets and stocks",
  "label_source": "bertopic",
  "keywords": [
    {"keyword": "stocks", "weight": 0.42},
    {"keyword": "market", "weight": 0.37}
  ],
  "document_count": 124,
  "document_examples": [
    "Stocks climbed after the earnings report ...",
    "Markets opened higher as investors ..."
  ]
}
```

Use `document_examples` as a sanity check, then trace `document_ids` back to the corpus for deeper inspection.

## Configuration reference

Topic modeling configurations use a strict schema. Unknown fields or type mismatches are errors.

### Text source

- `text_source.sample_size`: Limit the number of documents used for analysis.
- `text_source.min_text_characters`: Drop documents shorter than this count.

### LLM extraction

- `llm_extraction.enabled`: Enable the LLM extraction stage.
- `llm_extraction.method`: `single` or `itemize` to control whether an input maps to one or many documents.
- `llm_extraction.client`: LLM client configuration (requires `biblicus[openai]`).
- `llm_extraction.prompt_template`: Prompt template for the extraction stage.
- `llm_extraction.system_prompt`: Optional system prompt.

### Entity removal

- `entity_removal.enabled`: Enable local named-entity removal.
- `entity_removal.provider`: `spacy` (required).
- `entity_removal.model`: spaCy model name (for example `en_core_web_sm`).
- `entity_removal.entity_types`: Entity labels to remove. Empty uses defaults.
- `entity_removal.replace_with`: Replacement text inserted for removed entities.
- `entity_removal.collapse_whitespace`: Normalize whitespace after removals.
- `entity_removal.regex_patterns`: Optional regex patterns applied after NER.
- `entity_removal.regex_replace_with`: Replacement text for regex removals.

### Lexical processing

- `lexical_processing.enabled`: Enable normalization.
- `lexical_processing.lowercase`: Lowercase text before tokenization.
- `lexical_processing.strip_punctuation`: Remove punctuation before tokenization.
- `lexical_processing.collapse_whitespace`: Normalize repeated whitespace.

### BERTopic configuration

- `bertopic_analysis.parameters`: Mapping of BERTopic constructor parameters.
- `bertopic_analysis.vectorizer.ngram_range`: Inclusive n-gram range (for example `[1, 2]`).
- `bertopic_analysis.vectorizer.stop_words`: `english` or a list of stop words. Set to `null` to disable.
- `bertopic_analysis.umap_model.parameters`: Mapping forwarded to `umap.UMAP`.
- `bertopic_analysis.hdbscan_model.parameters`: Mapping forwarded to `hdbscan.HDBSCAN`.
- `bertopic_analysis.representation_model`: Optional BERTopic representation model configuration.

### BERTopic representation model

Biblicus supports BERTopic's OpenAI representation model for LLM-generated topic labels. The representation model is
passed into the BERTopic constructor, so topic labels remain part of the BERTopic fit instead of a separate Biblicus
post-processing stage.

```yaml
bertopic_analysis:
  representation_model:
    provider: openai
    model: gpt-5.4-mini
    nr_docs: 4
    delay_in_seconds: 0
    prompt_template: |
      I have a topic that contains the following documents:
      [DOCUMENTS]

      The topic is described by these keywords:
      [KEYWORDS]

      Return a short, specific AI/ML topic label.
```

The OpenAI representation model requires the `openai` package and an OpenAI API key from the environment or Biblicus
user configuration. The prompt template is the BERTopic prompt, so it uses `[KEYWORDS]` and `[DOCUMENTS]`.

## Vectorizer configuration

Biblicus forwards BERTopic configuration through `bertopic_analysis.parameters` and exposes vectorizer settings
through `bertopic_analysis.vectorizer`. To include bigrams, set `ngram_range` to `[1, 2]`. To remove stop words,
set `stop_words` to `english` or a list.

```yaml
bertopic_analysis:
  parameters:
    min_topic_size: 10
    nr_topics: 12
  vectorizer:
    ngram_range: [1, 2]
    stop_words: english
```

## AI-ML-Research fine discovery

The official first-pass discovery input for the AI-ML-Research corpus is metadata-derived text containing only the
title and abstract:

```bash
biblicus extract build \
  --corpus corpora/AI-ML-research \
  --configuration configurations/extraction/ai-ml-research-topic-abstracts.yml \
  --force
```

The recipe uses:

```yaml
extractor_id: metadata-text
configuration:
  fields:
    - title
    - metadata.abstract
```

Tags and curation metadata are intentionally excluded so blind candidate labels do not leak into unsupervised topic
discovery.

Run a granularity sweep against the metadata snapshot:

```bash
biblicus analyze topic-granularity-sweep \
  --corpus corpora/AI-ML-research \
  --configuration configurations/topic-modeling/ai-ml-research-fine.yml \
  --extraction-snapshot pipeline:<snapshot_id> \
  --target-topic-range 10:20 \
  --format markdown
```

The sweep runs `coarse`, `balanced`, and `fine` profiles without representation labels, selects the best profile for
the requested range, and reruns the selected profile with BERTopic OpenAI labels.

## Research agent topic context

Research agents need a compact map of what is already in a knowledge base before they search for new related
material. Generate that context from a topic-modeling snapshot:

```bash
biblicus analyze topic-context \
  --corpus corpora/AI-ML-research \
  --topic-modeling-snapshot <topic_modeling_snapshot_id> \
  --max-topics 20 \
  --examples-per-topic 3 \
  --summary-model gpt-5.4-mini \
  --format markdown
```

The command writes artifacts under `analysis/topic-context/<snapshot_id>/` and prints either JavaScript Object
Notation or Markdown. Markdown is the research-agent handoff format. It includes the topic label, topic identifier,
document count, keywords, and representative examples. Examples include title, subtitle when present, source,
publication date when present, and an abstract or summary.

Representative examples are deterministic, not random. Biblicus scores each document by similarity to the other
documents assigned to the same topic and keeps the most central examples first. The command excludes BERTopic's
outlier topic `-1` unless `--include-outlier` is passed.

When `--summary-model` is provided, Biblicus asks OpenAI for concise topic guidance and for summaries of examples
that do not have abstract-like metadata. The report remains context only: it does not edit classifier manifests,
accept governance proposals, or promote examples into seeds.

## Repeatable integration script

The integration script downloads AG News, runs extraction, and then runs topic modeling with the selected
parameters. It prints a summary with the analysis snapshot identifier and the output path.

```
python scripts/topic_modeling_integration.py --corpus corpora/ag_news_demo --force
```

### Example: raise topic count

```
python scripts/topic_modeling_integration.py \
  --corpus corpora/ag_news_demo \
  --force \
  --limit 10000 \
  --vectorizer-ngram-min 1 \
  --vectorizer-ngram-max 2 \
  --bertopic-param nr_topics=8 \
  --bertopic-param min_topic_size=2
```

### Example: disable lexical processing and restrict inputs

```
python scripts/topic_modeling_integration.py \
  --corpus corpora/ag_news_demo \
  --force \
  --sample-size 200 \
  --min-text-characters 200 \
  --no-lexical-enabled
```

### Example: keep lexical processing but preserve punctuation

```
python scripts/topic_modeling_integration.py \
  --corpus corpora/ag_news_demo \
  --force \
  --no-lexical-strip-punctuation
```

BERTopic parameters are passed directly to the constructor. Use repeated `--bertopic-param key=value` pairs for
multiple parameters. Values that look like JSON objects or arrays are parsed as JSON.

The integration script requires at least 16 documents to avoid BERTopic default UMAP errors. Increase `--limit` or
use a larger corpus if you receive a small-corpus error.

AG News downloads require the `datasets` dependency. Install with:

```
python -m pip install "biblicus[datasets,topic-modeling]"
```

## Tuning workflow

Start with a small sample to validate the pipeline, then scale up:

1) Run with `--limit 500` to validate extraction and output structure.
2) Add bigrams and stop words to reduce noise in keyword lists.
3) Increase `--limit` or `--sample-size` once topics look stable.
4) Experiment with `nr_topics`, UMAP, and HDBSCAN settings to control granularity, or use
   `topic-granularity-sweep` to compare the built-in profiles.

## Interpreting results

When a topic looks off, inspect the `document_examples` and compare them to the keyword list. If the documents do not
match the keywords, adjust lexical processing or increase `min_topic_size` to reduce noise.

## Common pitfalls

- Using too few documents for BERTopic defaults (aim for at least 16).
- Forgetting to enable stop words and ending up with filler topics.
- Comparing runs that used different extraction prompts or lexical settings.

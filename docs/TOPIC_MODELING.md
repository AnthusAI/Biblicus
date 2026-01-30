# Topic modeling

Biblicus provides a topic modeling analysis backend that reads extracted text artifacts, optionally applies an LLM
extraction pass, applies lexical processing, runs BERTopic, and optionally applies an LLM fine-tuning pass for
labels. The output is structured JavaScript Object Notation with explicit per-topic evidence.

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

- Text collection reads extracted text artifacts from an extraction run.
- LLM extraction optionally transforms each document into one or more analysis documents.
- Lexical processing optionally normalizes text before BERTopic.
- BERTopic produces topic assignments and keyword weights.
- LLM fine-tuning optionally replaces topic labels based on sampled documents.

## Output structure

Topic modeling writes a single `output.json` file under the analysis run directory. The output contains:

- `run.run_id` and `run.stats` for reproducible tracking.
- `report.topics` with the modeled topics.
- `report.text_collection`, `report.llm_extraction`, `report.lexical_processing`, `report.bertopic_analysis`,
  and `report.llm_fine_tuning` describing each pipeline stage.

Each topic record includes:

- `topic_id`: The BERTopic topic identifier. The outlier topic uses `-1`.
- `label`: The human-readable label.
- `label_source`: `bertopic` or `llm` depending on the stage that set the label.
- `keywords`: Keyword list with weights.
- `document_count`: Number of documents assigned to the topic.
- `document_ids`: Item identifiers for the assigned documents.
- `document_examples`: Sampled document text used for inspection.

Per-topic behavior is determined by the BERTopic assignments and the optional fine-tuning stage. The lexical
processing flags can substantially change tokenization and therefore the resulting topic labels. The outlier
`topic_id` `-1` indicates documents that BERTopic could not confidently assign to a cluster.

## Configuration reference

Topic modeling recipes use a strict schema. Unknown fields or type mismatches are errors.

### Text source

- `text_source.sample_size`: Limit the number of documents used for analysis.
- `text_source.min_text_characters`: Drop documents shorter than this count.

### LLM extraction

- `llm_extraction.enabled`: Enable the LLM extraction stage.
- `llm_extraction.method`: `single` or `itemize` to control whether an input maps to one or many documents.
- `llm_extraction.client`: LLM client configuration (requires `biblicus[openai]`).
- `llm_extraction.prompt_template`: Prompt template for the extraction stage.
- `llm_extraction.system_prompt`: Optional system prompt.

### Lexical processing

- `lexical_processing.enabled`: Enable normalization.
- `lexical_processing.lowercase`: Lowercase text before tokenization.
- `lexical_processing.strip_punctuation`: Remove punctuation before tokenization.
- `lexical_processing.collapse_whitespace`: Normalize repeated whitespace.

### BERTopic configuration

- `bertopic_analysis.parameters`: Mapping of BERTopic constructor parameters.
- `bertopic_analysis.vectorizer.ngram_range`: Inclusive n-gram range (for example `[1, 2]`).
- `bertopic_analysis.vectorizer.stop_words`: `english` or a list of stop words. Set to `null` to disable.

### LLM fine-tuning

- `llm_fine_tuning.enabled`: Enable LLM topic labeling.
- `llm_fine_tuning.client`: LLM client configuration.
- `llm_fine_tuning.prompt_template`: Prompt template containing `{keywords}` and `{documents}`.
- `llm_fine_tuning.system_prompt`: Optional system prompt.
- `llm_fine_tuning.max_keywords`: Maximum keywords included per prompt.
- `llm_fine_tuning.max_documents`: Maximum documents included per prompt.

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

## Repeatable integration script

The integration script downloads AG News, runs extraction, and then runs topic modeling with the selected
parameters. It prints a summary with the analysis run identifier and the output path.

```
python3 scripts/topic_modeling_integration.py --corpus corpora/ag_news_demo --force
```

### Example: raise topic count

```
python3 scripts/topic_modeling_integration.py \
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
python3 scripts/topic_modeling_integration.py \
  --corpus corpora/ag_news_demo \
  --force \
  --sample-size 200 \
  --min-text-characters 200 \
  --no-lexical-enabled
```

### Example: keep lexical processing but preserve punctuation

```
python3 scripts/topic_modeling_integration.py \
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
python3 -m pip install "biblicus[datasets,topic-modeling]"
```

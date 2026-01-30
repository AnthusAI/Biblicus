# Topic modeling

Biblicus provides a topic modeling analysis backend that reads extracted text artifacts, optionally applies an LLM
extraction pass, applies lexical processing, runs BERTopic, and optionally applies an LLM fine-tuning pass for
labels. The output is structured JavaScript Object Notation with explicit per-topic evidence.

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

## Repeatable integration script

The integration script downloads a small Wikipedia corpus, runs extraction, and then runs topic modeling with
the selected parameters. It prints a summary with the analysis run identifier and the output path.

```
python3 scripts/topic_modeling_integration.py --corpus corpora/wiki_demo --force
```

### Example: raise topic count

```
python3 scripts/topic_modeling_integration.py \
  --corpus corpora/wiki_demo \
  --force \
  --limit 20 \
  --bertopic-param nr_topics=8 \
  --bertopic-param min_topic_size=2
```

### Example: disable lexical processing and restrict inputs

```
python3 scripts/topic_modeling_integration.py \
  --corpus corpora/wiki_demo \
  --force \
  --sample-size 20 \
  --min-text-characters 200 \
  --no-lexical-enabled
```

### Example: keep lexical processing but preserve punctuation

```
python3 scripts/topic_modeling_integration.py \
  --corpus corpora/wiki_demo \
  --force \
  --no-lexical-strip-punctuation
```

BERTopic parameters are passed directly to the constructor. Use repeated `--bertopic-param key=value` pairs for
multiple parameters. Values that look like JSON objects or arrays are parsed as JSON.

The integration script requires at least 16 documents to avoid BERTopic default UMAP errors. Increase `--limit` or
use a larger corpus if you receive a small-corpus error.

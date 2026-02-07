# Markov analysis

Biblicus provides a Markov analysis backend that learns a directed, weighted state transition graph from sequences of
text segments in a corpus. It is an exploratory analysis tool that produces structured, inspectable artifacts:

- A set of inferred states with per-state exemplars.
- A directed, weighted transition graph between states.
- A per-item decoded path that shows how each item traversed the state graph.
- Optional GraphViz exports for visualization.

Markov analysis is configured using YAML configurations, validated strictly, and stored as versioned snapshot artifacts under the
corpus. It is designed for experimentation across segmentation strategies and observation encodings.

## Observation encoder configurability

The observation encoder configuration is fully configurable. For hybrid encoders, you can control:

- `observations.categorical_source`: which observation field supplies categorical labels
- `observations.numeric_source`: which observation field supplies the numeric scalar

This allows hybrid encodings to use fields other than the defaults (for example, `llm_summary` or `segment_index`)
without changing the pipeline code.

## Topic-driven observations

Markov analysis can run topic modeling over segments and use the resulting topic labels as categorical observations.
This is useful when you want topic buckets to act as the observation symbols.

The topic modeling configuration is embedded inside the Markov configuration:

```
schema_version: 1
segmentation:
  method: sentence
topic_modeling:
  enabled: true
  configuration:
    schema_version: 1
    llm_extraction:
      enabled: false
    lexical_processing:
      enabled: false
    bertopic_analysis:
      parameters: {}
observations:
  categorical_source: topic_label
model:
  family: categorical
  n_states: 6
```

When enabled, the Markov observations include `topic_id` and `topic_label`. Setting
`observations.categorical_source` to `topic_label` makes the topic labels the categorical symbols
used by the Markov model.

Topic-driven runs emit extra debugging artifacts:

- `topic_modeling.json`: the full topic modeling report used for the run.
- `topic_assignments.jsonl`: per-segment topic assignments with the original segment text.
- `entity_removal.jsonl`: redacted segment text used for topic modeling (when enabled).

## What Markov analysis does

Markov analysis treats each item as a sequence:

1) Start from extracted text artifacts for a corpus item.
2) Segment the text into an ordered sequence (sentences, fixed windows, or provider-backed segmentation).
3) Convert each segment into an observation vector (categorical labels, numeric features, embeddings, or combinations).
4) Fit a hidden-state Markov model to learn:
   - latent states,
   - transition probabilities between states,
   - and per-state emission distributions.
5) Decode a most-likely state sequence for each item and emit the state transition graph.

## Text extract segmentation

Text extract is a provider-backed segmentation strategy designed for long documents. Instead of asking the model to
re-emit the entire text with labels, Biblicus gives the model a virtual file and asks it to insert XML tags in-place.
The model uses **str_replace tool calls** (old_str/new_str pairs), which Biblicus applies in memory.

This pattern has two benefits:

1) The model only emits a small edit script, which is cheaper and faster than reprinting the full transcript.
2) The original text remains intact; validation can prove that only tags were inserted.

Biblicus uses XML-style tags (`<span>...</span>`) so the edits are well-formed and easy to validate deterministically.

After applying the tags, Biblicus parses **spans** (the tagged text ranges). Interstitial content remains available
in the marked-up string without forcing the model to cover every token.

Example snippet:

System prompt excerpt:

**System prompt (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
Greeting. Verification. Resolution.
---
```

User prompt:

**User prompt:**

```
Return the segments that represent contiguous phases in the text.
```

Input text:

**Input text:**

```
Greeting. Verification. Resolution.
```

Marked-up text:

**Marked-up text:**

```
<span>Greeting.</span> <span>Verification.</span> <span>Resolution.</span>
```

Structured data:

**Structured data (result):**

```
{
  "marked_up_text": "<span>Greeting.</span> <span>Verification.</span> <span>Resolution.</span>",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 10, "text": "Greeting."},
    {"index": 2, "start_char": 11, "end_char": 24, "text": "Verification."},
    {"index": 3, "start_char": 25, "end_char": 37, "text": "Resolution."}
  ],
  "warnings": []
}
```

## Run Markov analysis from the CLI

```
biblicus analyze markov --corpus corpora/ag_news_demo_2k --configuration configurations/markov/local-discovery.yml
```

Example span markup configuration (text extract provider-backed):

```
schema_version: 1
segmentation:
  method: span_markup
  span_markup:
    client:
      provider: openai
      model: gpt-4o-mini
      api_key: null
      response_format: json_object
    system_prompt: |
      You are a virtual file editor. Use the available tools to edit the text.
      Interpret the word “return” in the user’s request as: wrap the returned text
      with <span>...</span> in-place in the current text.

      Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.
      When finished, call done. Do NOT return JSON in the assistant message.

      Rules:
      - Use str_replace only.
      - old_str must match exactly once in the current text.
      - old_str and new_str must be non-empty strings.
      - new_str must be identical to old_str with only <span> and </span> inserted.
      - Do not include <span> or </span> inside old_str or new_str.
      - Do not insert nested spans.
      - If a tool call fails due to non-unique old_str, retry with a longer unique old_str.
      - If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.
      - Do not delete, reorder, paraphrase, or label text.
      Current text:
      ---
      {text}
      ---
    prompt_template: |
      Return the segments that represent contiguous phases in the text.

      Rules:
      - Preserve original order.
      - Do not add labels, summaries, or commentary.
      - Prefer natural boundaries like greeting/opening, identity verification, reason for call,
        clarification, resolution steps, handoff/escalation, closing.
      - Use speaker turn changes as possible boundaries, but keep multi-turn exchanges together if they
        form a single phase.
      - Avoid extremely short fragments; merge tiny leftovers into a neighboring span.
model:
  family: gaussian
  n_states: 4
observations:
  encoder: tfidf
```

When no extraction snapshot is provided, Markov analysis looks for a default recipe at
`corpora/<Corpus>/recipes/extraction/default.yml` and builds or reuses the matching snapshot.
Recipes can include an optional `max_workers` field to control extraction concurrency. To keep
runs reproducible, pass an extraction snapshot explicitly:

```
biblicus analyze markov \
  --corpus corpora/ag_news_demo_2k \
  --configuration configurations/markov/local-discovery.yml \
  --extraction-snapshot pipeline:RUN_ID
```

### Cascading configurations and CLI overrides

Markov analysis configurations support cascading composition. You can pass multiple `--configuration` files; later configurations override
earlier configurations via a deep merge:

```
biblicus analyze markov \
  --corpus corpora/ag_news_demo_2k \
  --configuration configurations/markov/base.yml \
  --configuration configurations/markov/guided.yml
```

To override the composed configuration view from the command line, use `--config key=value` with dotted keys:

```
biblicus analyze markov \
  --corpus corpora/ag_news_demo_2k \
  --configuration configurations/markov/base.yml \
  --configuration configurations/markov/guided.yml \
  --config model.n_states=14
```

Omitted fields use the default values from the Markov analysis schema. Missing required fields remain hard errors.

## LLM observation cache

When `llm_observations.enabled` is true, Biblicus caches per-segment labels and summaries so you can rerun Markov analysis without
re-labeling the same text. The cache is keyed by the LLM client configuration (minus the API key), the prompt templates, and an
optional `cache_name`, so changing prompts or models creates a fresh cache automatically. Use `llm_observations.cache.cache_name`
to version caches for experiments.

Cache location:

```
.biblicus/cache/markov/llm-observations/<cache_id>/<extractor_id>/<snapshot_id>/
```

The cache is updated incrementally. If a prior run stopped partway through, rerunning the analysis will only label the missing
segments and continue.

To disable caching, set:

```
llm_observations:
  cache:
    enabled: false
```

## Output location and artifacts

Markov analysis output is stored under:

```
analysis/markov/<snapshot_id>/
```

The snapshot directory contains a manifest and structured artifacts. The canonical output is `output.json`. Additional files
provide intermediate visibility, such as segments and observations used to fit the model. When enabled, GraphViz output
is written as `transitions.dot`.

## Working demo

The integration demo script is a working reference you can use as a starting point:

```
python scripts/markov_analysis_demo.py --corpus corpora/ag_news_demo_2k
```

If you want the script to download and ingest AG News into a fresh corpus directory, pass `--download` (this requires the
optional datasets dependency).

Markov analysis requires an optional dependency:

```
python -m pip install "biblicus[markov-analysis]"
```

The demo builds or reuses an extraction snapshot, executes Markov analysis with example configurations, and prints the resulting run
paths. Inspect the emitted `output.json` and graph artifacts to understand states and transitions.

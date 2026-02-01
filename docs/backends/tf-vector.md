# TF Vector backend

The TF Vector backend implements a deterministic vector space model baseline using term-frequency vectors and cosine
similarity. It builds no persistent index and scores items at query time. This makes it useful as a lightweight
“vector-style” baseline without dense embeddings or external services.

## When to use it

- You want a minimal baseline to compare against lexical search.
- You want deterministic, inspectable similarity scoring.
- You are teaching retrieval concepts and want a small, runnable backend.

## Backend ID

`tf-vector`

## How it works

1) Tokenize the query and each item into lowercase word tokens.
2) Build term-frequency vectors.
3) Compute cosine similarity between the query vector and each item vector.
4) Return evidence ranked by similarity score.

## Configuration

The backend accepts these configuration fields:

- `snippet_characters`: maximum characters to include in evidence snippets.
- `extraction_run`: optional extraction run reference (`extractor_id:run_id`).

Example recipe:

```yaml
snippet_characters: 320
extraction_run: pipeline:RUN_ID
```

## Build a run

```
python -m biblicus build --corpus corpora/example --backend tf-vector --config extraction_run=pipeline:RUN_ID
```

This backend does not create artifacts beyond the run manifest.

## Query a run

```
python -m biblicus query --corpus corpora/example --run tf-vector:RUN_ID --query "semantic match"
```

The evidence results include a `stage` value of `tf-vector` and similarity scores for each match.

## What it is not

- This backend does not compute dense embeddings.
- It does not use approximate nearest neighbor indexing.
- It does not depend on external services.


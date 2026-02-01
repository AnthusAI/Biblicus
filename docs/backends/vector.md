# Vector backend

The vector backend implements a deterministic term-frequency vector similarity search. It builds no persistent index and
scores items at query time using cosine similarity between term-frequency vectors. This makes it useful as a lightweight
semantic-style baseline without relying on embeddings or external services.

## When to use it

- You want a minimal vector-style baseline to compare against lexical search.
- You need deterministic, inspectable similarity scoring.
- You are teaching retrieval concepts and want a small, runnable backend.

## Backend ID

`vector`

## How it works

1) Tokenize the query and each item into lowercase word tokens.
2) Build term-frequency vectors.
3) Compute cosine similarity between the query vector and each item vector.
4) Return evidence ranked by similarity score.

## Configuration

The vector backend accepts these configuration fields:

- `snippet_characters`: maximum characters to include in evidence snippets.
- `extraction_run`: optional extraction run reference (`extractor_id:run_id`).

Example recipe:

```yaml
snippet_characters: 320
extraction_run: pipeline:RUN_ID
```

## Build a run

```
python -m biblicus build --corpus corpora/example --backend vector --config extraction_run=pipeline:RUN_ID
```

The vector backend does not create artifacts beyond the run manifest, so builds are fast and deterministic.

## Query a run

```
python -m biblicus query --corpus corpora/example --run vector:RUN_ID --query "semantic match"
```

The evidence results include a `stage` value of `vector` and similarity scores for each match.

## What it is not

- This backend does not compute dense embeddings.
- It does not use approximate nearest neighbor indexing.
- It does not depend on external services.


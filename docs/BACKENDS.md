# Adding a Retrieval Backend

Backends are pluggable engines that implement a small, stable interface.
The goal is to make new retrieval ideas easy to test without reshaping the corpus.

For user documentation on available backends, see the [Backend Reference](backends/index.md).

## Backend contract

Backends implement two operations:

- **Build run**: create a `RetrievalRun` manifest (and optional artifacts).
- **Query**: return structured `Evidence` objects under a `QueryBudget`.

## Implementation checklist

1. **Define a Pydantic configuration model** for your backend recipe.
2. **Implement `RetrievalBackend`**:
   - `build_run(corpus, recipe_name, config)`
   - `query(corpus, run, query_text, budget)`
3. **Emit `Evidence`** with required fields:
   - `item_id`, `source_uri`, `media_type`, `score`, `rank`, `stage`, `recipe_id`, `run_id`
   - `text` **or** `content_ref`
4. **Register the backend** in `biblicus.backends.available_backends`.
5. **Add behavior-driven development specifications** before implementation and make them pass with 100% coverage.

## Design notes

- Treat **runs** as immutable manifests with reproducible parameters.
- If your backend needs artifacts, store them under `.biblicus/runs/` and record paths in `artifact_paths`.
- Keep **text extraction** in explicit pipeline stages, not in backend ingestion.
  See `docs/EXTRACTION.md` for how extraction runs are built and referenced from backend configs.

## Examples

See:

- `biblicus.backends.scan.ScanBackend` (minimal baseline)
- `biblicus.backends.sqlite_full_text_search.SqliteFullTextSearchBackend` (practical local backend)

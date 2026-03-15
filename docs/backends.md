# Adding a Retrieval Backend

Backends are pluggable engines that implement a small, stable interface.
The goal is to make new retrieval ideas easy to test without reshaping the corpus.

For user documentation on available backends, see the [Backend Reference](backends/index.md).

## Backend contract

Backends implement two operations:

- **Build run**: create a `RetrievalRun` manifest (and optional artifacts).
- **Query**: return structured `Evidence` objects under a `QueryBudget`.

## Run artifacts

Backends store artifacts and manifests under:

```
retrieval/<backend_id>/<snapshot_id>/
  manifest.json
  <backend artifacts>
```

The manifest is the reproducible contract. Artifacts are backend-specific and listed in `artifact_paths`.

## Implementation checklist

1. **Define a Pydantic configuration model** for your backend configuration.
2. **Implement `RetrievalBackend`**:
   - `build_run(corpus, configuration_name, config)`
   - `query(corpus, run, query_text, budget)`
3. **Emit `Evidence`** with required fields:
   - `item_id`, `source_uri`, `media_type`, `score`, `rank`, `stage`, `configuration_id`, `snapshot_id`
   - `text` **or** `content_ref`
4. **Register the backend** in `biblicus.backends.available_backends`.
5. **Add behavior-driven development specifications** before implementation and make them pass with 100% coverage.

## Design notes

- Treat **runs** as immutable manifests with reproducible parameters.
- If your backend needs artifacts, store them under `retrieval/` and record paths in `artifact_paths`.
- Keep **text extraction** in explicit pipeline stages, not in backend ingestion.
  See `docs/extraction.md` for how extraction snapshots are built and referenced from backend configs.

## Reproducibility checklist

- Record the extraction snapshot reference used to build the backend.
- Keep the backend configuration configuration in source control.
- Reuse the same `QueryBudget` when comparing backends.

## Common pitfalls

- Returning evidence without `text` or `content_ref`.
- Mutating artifacts after a run is created (breaks reproducibility).
- Comparing runs built from different extraction outputs.

## Examples

See:

- `biblicus.retrievers.scan.ScanRetriever` (minimal baseline)
- `biblicus.retrievers.sqlite_full_text_search.SqliteFullTextSearchRetriever` (practical local backend)
- `biblicus.retrievers.tf_vector.TfVectorRetriever` (term-frequency vector baseline; `tf-vector`)

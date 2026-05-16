# Standard Single-Item Ingest

## Press Release

Biblicus now has a standard command-line path for storing one already-retrieved local item with curated metadata. Agents can pass a local file, a metadata file, and explicit provenance to `biblicus ingest`; Biblicus writes the canonical raw item, sidecar metadata, and catalog entry through the existing item-centered ingest primitive.

## FAQ

### Does this download or enrich content?

No. Retrieval, download, citation lookup, and metadata enrichment happen before calling Biblicus. This workflow only stores bytes and metadata in the corpus format.

### What is the standard command?

Use `biblicus ingest <local-file> --metadata-file <metadata.yml> --source-uri <uri>`.
When the source publication date is known, add `--published-at YYYY-MM-DD`. Use `--updated-at` and `--retrieved-at` only when those dates are known.

### Why extend `ingest` instead of adding a new command?

`ingest` is already the official single-item command-line verb. The missing piece was exposing the existing metadata-capable storage primitive from the command line.

### What does Biblicus write?

For non-Markdown items, Biblicus writes the raw file and a `.biblicus.yml` sidecar containing media type, tags, curated metadata, and the `biblicus` provenance block. The catalog is updated immediately.

### What metadata format is accepted?

The metadata file must be a YAML or JSON mapping. Publication dates live under `dates.published_at`; top-level `published` metadata is not accepted for new ingest. Lists, scalars, invalid syntax, and missing files are user errors.

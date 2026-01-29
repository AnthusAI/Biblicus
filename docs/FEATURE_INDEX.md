# Feature index

This document lists the major capabilities that exist today and points you to:

- Behavior specifications in `features/*.feature`
- Documentation pages in `docs/`
- Primary implementation modules in `src/biblicus/`

The behavior specifications are the authoritative definition of behavior. The documentation is a narrative guide.

## Corpus

What it does:

- Creates a file based corpus with raw items and a rebuildable catalog.
- Ingests local files, web addresses, and text notes.
- Stores metadata in Markdown front matter or sidecar files.

Documentation:

- `docs/CORPUS.md`
- `docs/CORPUS_DESIGN.md`

Behavior specifications:

- `features/biblicus_corpus.feature`
- `features/corpus_identity.feature`
- `features/corpus_edge_cases.feature`
- `features/corpus_purge.feature`
- `features/ingest_sources.feature`

Primary implementation:

- `src/biblicus/corpus.py`
- `src/biblicus/sources.py`
- `src/biblicus/frontmatter.py`
- `src/biblicus/uris.py`

## Import and ignore rules

What it does:

- Imports an existing folder tree while preserving relative paths.
- Applies ignore rules from a `.biblicusignore` file.

Documentation:

- `docs/CORPUS.md`

Behavior specifications:

- `features/import_tree.feature`

Primary implementation:

- `src/biblicus/corpus.py`
- `src/biblicus/ignore.py`

## Streaming ingest

What it does:

- Supports ingestion of large binary items from a stream without loading all bytes into memory.

Behavior specifications:

- `features/streaming_ingest.feature`

Primary implementation:

- `src/biblicus/corpus.py`

## Lifecycle hooks

What it does:

- Defines explicit hook points for ingestion and catalog rebuild.
- Validates hook input and output models and records hook execution.

Documentation:

- `docs/CORPUS_DESIGN.md`

Behavior specifications:

- `features/lifecycle_hooks.feature`
- `features/hook_config_validation.feature`
- `features/hook_error_handling.feature`
- `features/python_hook_logging.feature`

Primary implementation:

- `src/biblicus/hooks.py`
- `src/biblicus/hook_manager.py`
- `src/biblicus/hook_logging.py`

## User configuration files

What it does:

- Loads machine-specific configuration for optional integrations.
- Supports home and local configuration file locations.

Documentation:

- `docs/USER_CONFIGURATION.md`

Behavior specifications:

- `features/user_config.feature`

Primary implementation:

- `src/biblicus/user_config.py`

## Text extraction stage

What it does:

- Builds extraction runs as a separate pipeline stage.
- Stores extracted text artifacts under the corpus so multiple extractors can coexist.
- Supports an explicit extractor pipeline through the `pipeline` extractor.
- Includes a Portable Document Format text extractor plugin.
- Includes a speech to text extractor plugin for audio items.
- Includes a selection extractor step for choosing extracted text within a pipeline.
- Includes a MarkItDown extractor plugin for document conversion.

Documentation:

- `docs/EXTRACTION.md`

Behavior specifications:

- `features/text_extraction_runs.feature`
- `features/extractor_pipeline.feature`
- `features/extractor_validation.feature`
- `features/extraction_selection.feature`
- `features/extraction_selection_longest.feature`
- `features/extraction_error_handling.feature`
- `features/ocr_extractor.feature`
- `features/stt_extractor.feature`
- `features/unstructured_extractor.feature`
- `features/markitdown_extractor.feature`
- `features/integration_unstructured_extraction.feature`

Primary implementation:

- `src/biblicus/extraction.py`
- `src/biblicus/extractors/`

## Retrieval backends

What it does:

- Builds and queries retrieval runs.
- Returns evidence as structured output.
- Supports a minimal scan backend and a practical Sqlite full text search backend.

Documentation:

- `docs/BACKENDS.md`

Behavior specifications:

- `features/retrieval_scan.feature`
- `features/retrieval_sqlite_full_text_search.feature`
- `features/retrieval_uses_extraction_run.feature`
- `features/retrieval_budget.feature`
- `features/retrieval_utilities.feature`
- `features/backend_validation.feature`

Primary implementation:

- `src/biblicus/retrieval.py`
- `src/biblicus/backends/`

## Evaluation

What it does:

- Evaluates retrieval runs against datasets and budgets.

Behavior specifications:

- `features/evaluation.feature`
- `features/model_validation.feature`

Primary implementation:

- `src/biblicus/evaluation.py`
- `src/biblicus/models.py`

## Context packs

What it does:

- Builds context pack text from retrieval evidence using an explicit policy.
- Fits a context pack to a token budget using an explicit tokenizer identifier.

Documentation:

- `docs/CONTEXT_PACK.md`

Behavior specifications:

- `features/context_pack.feature`
- `features/token_budget.feature`

Primary implementation:

- `src/biblicus/context.py`

## Knowledge base

What it does:

- Provides a turnkey interface that accepts a folder and returns a ready-to-query workflow.
- Applies sensible defaults for import, retrieval, and context pack shaping.

Behavior specifications:

- `features/knowledge_base.feature`

Primary implementation:

- `src/biblicus/knowledge_base.py`

## Testing, coverage, and documentation build

What it does:

- Runs behavior specifications under coverage and emits an Hypertext Markup Language coverage report.
- Builds Sphinx documentation from docstrings and documentation pages.

Documentation:

- `docs/TESTING.md`

Primary implementation:

- `scripts/test.py`
- `docs/conf.py`
- `.github/workflows/ci.yml`

## Integration corpora

What it does:

- Downloads small public datasets at runtime for integration scenarios.

Behavior specifications:

- `features/integration_wikipedia.feature`
- `features/integration_pdf_samples.feature`
- `features/integration_mixed_corpus.feature`
- `features/integration_mixed_extraction.feature`
- `features/integration_pdf_retrieval.feature`
- `features/integration_audio_samples.feature`

Integration scripts:

- `scripts/download_wikipedia.py`
- `scripts/download_pdf_samples.py`
- `scripts/download_mixed_samples.py`
- `scripts/download_audio_samples.py`

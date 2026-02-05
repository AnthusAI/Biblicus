# CHANGELOG


## v1.2.0 (2026-02-05)

### Bug Fixes

- Avoid prompting during extraction steps
  ([`99354fb`](https://github.com/AnthusAI/Biblicus/commit/99354fb9ae7ec869b3aa175784a86a9cd717e01a))

Add --auto-deps to extraction CLI calls in behavesteps.

- Tighten dependency relation filtering
  ([`b83de5a`](https://github.com/AnthusAI/Biblicus/commit/b83de5a63859adbea0f69c43ac1fab481b290155))

### Documentation

- Add baseline graph extractor guidance
  ([`816d59c`](https://github.com/AnthusAI/Biblicus/commit/816d59ce55adefb908e62870ff6512d902d1e504))

- Add graph extraction story report
  ([`a307b89`](https://github.com/AnthusAI/Biblicus/commit/a307b891114673a9793a15dfb5cc1829695fd168))

- Clarify graph properties and neo4j install
  ([`f7ddf35`](https://github.com/AnthusAI/Biblicus/commit/f7ddf35e32ca9dfa05f0088364f54fa98b12ea94))

### Features

- Add graph extraction stage and demos
  ([`56fa41f`](https://github.com/AnthusAI/Biblicus/commit/56fa41f9697cd8f321787a349c13d09c4068d0d2))

- Add IBM Heron layout detection and comprehensive OCR benchmarking
  ([`70d6fe1`](https://github.com/AnthusAI/Biblicus/commit/70d6fe1d65c6d7934109f2d31f01bd600764ef80))

- Implement HeronLayoutExtractor using IBM Research's Heron-101 models - Add two-stage layout-aware
  OCR pipeline (Heron → Tesseract) - Create comprehensive OCR benchmarking system with FUNSD dataset
  - Add PaddleOCR PP-Structure layout detection - Add Tesseract OCR extractor with layout metadata
  support - Benchmark 9 OCR pipelines with detailed metrics (F1, recall, WER, etc.) - Document Heron
  achieving highest recall (0.810) vs other methods - Clean up documentation structure (move to
  docs/guides/) - Remove proprietary references

Heron Results: - F1: 0.519, Recall: 0.810 (highest), Bigram: 0.561 (best ordering) - Detects 24
  regions vs PaddleOCR's 8 - Trade-off: higher recall but lower precision

See docs/guides/ocr-benchmarking.md for complete guide.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- Add metadata field to extraction pipeline for layout-aware OCR
  ([`65c1969`](https://github.com/AnthusAI/Biblicus/commit/65c196938630317fbfb1b67b864183c27a9bc5bc))

Add `metadata: Dict[str, Any]` field to ExtractedText and ExtractionStepOutput models with JSON file
  persistence. This enables pipeline stages to pass structured data (layout regions, bounding boxes,
  document analysis) to downstream stages.

## Background

Based on feedback from @uokesita about layout-aware OCR workflows: > For non-selectable files we use
  Heron to extract first the layout. Then > Tesseract to extract the text. Because some of the files
  that do not have > a linear layout are difficult to parse with the correct order.

This workflow requires passing structured analysis data between pipeline stages: - Layout detector
  outputs: regions, types, coordinates, reading order - OCR stage reads layout metadata to process
  regions in correct order - Text reconstruction merges results based on layout analysis

## Changes

### Models (src/biblicus/models.py) - Add `metadata: Dict[str, Any]` to ExtractedText - Add
  `metadata: Dict[str, Any]` to ExtractionStepOutput - Both default to empty dict for backward
  compatibility

### Extraction Pipeline (src/biblicus/extraction.py) - Add `metadata_relpath: Optional[str]` to
  ExtractionStepResult - Add `final_metadata_relpath: Optional[str]` to ExtractionItemResult - Add
  `write_extracted_metadata_artifact()` function - Add `write_pipeline_step_metadata_artifact()`
  function - Update pipeline loop to persist metadata as JSON files

### File Structure

Metadata is persisted alongside text artifacts:

``` .biblicus/snapshots/extraction/pipeline/{snapshot_id}/ ├── manifest.json ├── text/{item_id}.txt
  ├── metadata/{item_id}.json # NEW: Final metadata └── steps/ ├── 01-layout-detector/ │ ├──
  text/{item_id}.txt │ └── metadata/{item_id}.json # NEW: Step metadata └── 02-ocr-tesseract/ ├──
  text/{item_id}.txt └── metadata/{item_id}.json # NEW: Step metadata ```

## Usage Example

A layout detector can return structured metadata:

```python return ExtractedText( text="", # Analysis stage may not produce text
  producer_extractor_id="layout-detector", metadata={ "layout_type": "multi-column", "regions": [
  {"id": 1, "type": "header", "bbox": [0,0,100,50], "order": 1}, {"id": 2, "type": "table", "bbox":
  [0,50,100,200], "order": 2} ] } ) ```

Subsequent OCR extractor reads region data:

```python def extract_text(self, *, previous_extractions, ...): layout_data =
  previous_extractions[-1].metadata if "regions" in layout_data: # Process regions in order
  specified by layout detector for region in sorted(layout_data["regions"], key=lambda r:
  r["order"]): # OCR this region... ```

## Testing

All 933 existing BDD scenarios pass, confirming backward compatibility.

## Benefits

- **Transparent**: Metadata visible in filesystem as JSON files - **Repeatable**: Can re-run
  pipeline stages using persisted metadata - **Debuggable**: Inspect intermediate analysis results -
  **Backward compatible**: Existing extractors continue working unchanged

## Related

- Issue #4: Tesseract OCR extractor - Issue #5: Heron layout detection research

Thanks to @uokesita for the feature suggestion and OCR workflow insights.

- Add ner and dependency graph extractors
  ([`6fc2bf2`](https://github.com/AnthusAI/Biblicus/commit/6fc2bf23c12e444de8a99641273382bedde59393))

- Add workflow dependency planning
  ([`fa3cc62`](https://github.com/AnthusAI/Biblicus/commit/fa3cc62612a710398abe5ba2590a03f79466631c))

- Expand real integration coverage
  ([`b3b9914`](https://github.com/AnthusAI/Biblicus/commit/b3b99149a23f5f22de6d33b951dc6db3bac30386))

- Harden dependency plans and coverage
  ([`fc6d0e0`](https://github.com/AnthusAI/Biblicus/commit/fc6d0e0166328d780479f528b6b40067fc210feb))

- Wire dependency plans into biblicus cli
  ([`f3c071c`](https://github.com/AnthusAI/Biblicus/commit/f3c071c61acd3e248522231d9bc3ecd068a21430))

Add CLI dependency execution for build/query and specs. Fix ruff issues in workflow-related modules.

### Testing

- Add baseline graph extractor specs
  ([`2a35abf`](https://github.com/AnthusAI/Biblicus/commit/2a35abfa008a3f166cb72a04fc543519c9a0d4e8))

- Cover dependency length filters
  ([`4e741e3`](https://github.com/AnthusAI/Biblicus/commit/4e741e3dcb03cd65379d6bf64f68c579bc618292))

- Cover OCR and dependency branches
  ([`536986e`](https://github.com/AnthusAI/Biblicus/commit/536986ed0a70c4b7a4b4c3cb0de04e5b5811e5a0))

- Reset fake spacy state per scenario
  ([`efb8a8e`](https://github.com/AnthusAI/Biblicus/commit/efb8a8e763cbae763e847bde9860e869304150f3))

- Stabilize short relation coverage
  ([`e51f50f`](https://github.com/AnthusAI/Biblicus/commit/e51f50f79873ed6bde93104a7048810ca79a2000))


## v1.1.2 (2026-02-03)

### Bug Fixes

- **sqlite-fts**: Strip punctuation from query tokens to avoid FTS5 syntax errors
  ([#1](https://github.com/AnthusAI/Biblicus/pull/1),
  [`1cdac23`](https://github.com/AnthusAI/Biblicus/commit/1cdac2309f25d2551fd2cdd3c33106c149120d07))

Strip punctuation from query tokens to prevent FTS5 syntax errors.

Fixes queries like 'what agreement do we have with Acme?' where '?' was being interpreted as FTS5
  wildcard syntax.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Documentation

- Fix class path references in backends.md
  ([`9ddefa4`](https://github.com/AnthusAI/Biblicus/commit/9ddefa46993ec9775248feae57d0ff7a8baa0861))

Update references from old backend class names to current retriever names: -
  biblicus.backends.scan.ScanBackend → biblicus.retrievers.scan.ScanRetriever -
  biblicus.backends.sqlite_full_text_search.SqliteFullTextSearchBackend →
  biblicus.retrievers.sqlite_full_text_search.SqliteFullTextSearchRetriever -
  biblicus.backends.vector.VectorBackend → biblicus.retrievers.tf_vector.TfVectorRetriever

Thanks to @uokesita for identifying this inconsistency in PR #3.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>


## v1.1.1 (2026-02-03)

### Bug Fixes

- Rename docs to kebab-case and clean up content
  ([`3d71c10`](https://github.com/AnthusAI/Biblicus/commit/3d71c107b52d6aea62606bb7d50946a4f4ca3db9))


## v1.1.0 (2026-02-03)


## v1.0.0 (2026-02-02)

### Bug Fixes

- **context-engine**: Cover empty pack branch
  ([`e925b2a`](https://github.com/AnthusAI/Biblicus/commit/e925b2a6a58406f85a7fbe43a9797d32e08cf4de))

- **context-engine**: Cover pack insertion branches
  ([`b4d81b5`](https://github.com/AnthusAI/Biblicus/commit/b4d81b54adeb299bb8394b1c9637b14b4af5e9af))

### Features

- Add tool loop uniqueness safeguards
  ([`ad93e8a`](https://github.com/AnthusAI/Biblicus/commit/ad93e8a3f0602be09c31f22603c86654c2608b89))

- **context-engine**: Add composable context engine
  ([`437fa2e`](https://github.com/AnthusAI/Biblicus/commit/437fa2e0a8daa583a87d503acba7b1f19a08e188))

Add Context engine models, compaction, retrieval expansion, and extensive BDD coverage plus docs and
  demos.

BREAKING CHANGE: Context and retriever APIs and configs are reworked; update integrations to new
  Context engine primitives.

- **theme**: Add custom Biblicus theme
  ([`834ea43`](https://github.com/AnthusAI/Biblicus/commit/834ea430214c479d203f4834aa1ced1123fa2ae4))

### Refactoring

- Align retrieval configuration and vocabulary
  ([`6ca6edf`](https://github.com/AnthusAI/Biblicus/commit/6ca6edfc87cb3b0ffafe319ab72427133358652d))


## v0.16.0 (2026-02-01)

### Bug Fixes

- Normalize front matter body
  ([`eb6b3e7`](https://github.com/AnthusAI/Biblicus/commit/eb6b3e78d6df086085675fe24fad0a9d56c5142e))

### Documentation

- Add biblicus theme styling
  ([`10b81a4`](https://github.com/AnthusAI/Biblicus/commit/10b81a42079cdcd7dceda62fba492e2160404ebe))

- Reorganize retrieval and backend docs
  ([`2831456`](https://github.com/AnthusAI/Biblicus/commit/2831456a72edf2bd70cff8784aea4bb07fce124c))

### Features

- Add chunked retrievers and offset pagination
  ([`cbfe57f`](https://github.com/AnthusAI/Biblicus/commit/cbfe57f911929c36efdbe38426fb255a8ecff575))

- Harden markov boundary embeddings
  ([`e3b525e`](https://github.com/AnthusAI/Biblicus/commit/e3b525eee25d2e989f31fd4de197d0025d85f869))


## v0.15.1 (2026-02-01)

### Bug Fixes

- Align logo in readme
  ([`d21e422`](https://github.com/AnthusAI/Biblicus/commit/d21e4226b8ee06fc41afe8250670b63c3bfc4550))

### Documentation

- Update roadmap
  ([`e4a033e`](https://github.com/AnthusAI/Biblicus/commit/e4a033eada6ede8db56032ef92a5964811f04d67))

### Testing

- Fetch and cache wikitext2 fixtures in CI
  ([`bf72e89`](https://github.com/AnthusAI/Biblicus/commit/bf72e892779d2ec1604e215305eccc33d784538c))


## v0.15.0 (2026-02-01)

### Bug Fixes

- Correct word-split regex checks in text utility steps
  ([`f2e280b`](https://github.com/AnthusAI/Biblicus/commit/f2e280b799d263608be302597136749ade3ec7ae))

- Improve text utilities introduction
  ([`dbf52b5`](https://github.com/AnthusAI/Biblicus/commit/dbf52b5b3ede456f6b6f4f843baeb861378be048))

- Satisfy ruff and black
  ([`cf8211f`](https://github.com/AnthusAI/Biblicus/commit/cf8211f475e9c3685056694ee2b92a58741df0e6))

- **ai**: Remove duplicate feature specs
  ([`62f3cb4`](https://github.com/AnthusAI/Biblicus/commit/62f3cb4dd24655a599614a7a9e0b47529346fb66))

### Documentation

- Add analysis backend selection guidance
  ([`fd8d76d`](https://github.com/AnthusAI/Biblicus/commit/fd8d76d04813679808df83814cb0388fae65e436))

- Add context pack before-and-after example
  ([`289c763`](https://github.com/AnthusAI/Biblicus/commit/289c763c66f69efcb6b13ebaa17f4a0bc29ba2a6))

- Add evidence lifecycle overview
  ([`c01ff7a`](https://github.com/AnthusAI/Biblicus/commit/c01ff7a596182e281ee00315d101768c91157e7e))

- Add profiling comparison workflow
  ([`ff46df6`](https://github.com/AnthusAI/Biblicus/commit/ff46df6d99bc33b03832f33d9cef72f2ae7b28bd))

- Add retrieval evaluation diagnostics guidance
  ([`53d93c6`](https://github.com/AnthusAI/Biblicus/commit/53d93c666fba8af4498ddd9f2bb132ffad079f4e))

- Add retrieval evidence inspection workflow
  ([`a8b0faa`](https://github.com/AnthusAI/Biblicus/commit/a8b0faa7184076fc6a3626f48d3ce864a3a08c27))

- Add retrieval evidence retention guidance
  ([`647ec04`](https://github.com/AnthusAI/Biblicus/commit/647ec0439d44c170c725d2b1e149bb72702619fd))

- Add retrieval quality evidence tracing
  ([`922b61d`](https://github.com/AnthusAI/Biblicus/commit/922b61d603f07391bc6d704aec8c73d39cad9ca0))

- Add topic modeling interpretation guidance
  ([`d508a5d`](https://github.com/AnthusAI/Biblicus/commit/d508a5de536de6fc06cd2baf6849044f5f7c2d9c))

- Expand analysis and profiling textbook
  ([`5411a59`](https://github.com/AnthusAI/Biblicus/commit/5411a5957d101f94ae1d783d1b828cde9a5b8030))

- Expand backend reference textbook
  ([`6f90114`](https://github.com/AnthusAI/Biblicus/commit/6f90114f23381eb8e00607c9e3f2b215a4d163d8))

- Expand backend textbook
  ([`b3ecf02`](https://github.com/AnthusAI/Biblicus/commit/b3ecf02343cc85ef14e7a52248b18e67083b0718))

- Expand context pack textbook
  ([`6d94e47`](https://github.com/AnthusAI/Biblicus/commit/6d94e479d7f2e2086340613c17d552cf2e0508af))

- Expand corpus design and architecture textbook
  ([`363219e`](https://github.com/AnthusAI/Biblicus/commit/363219ee0c51f3fc779af464ca5e7db11971de68))

- Expand corpus textbook
  ([`a28cf3f`](https://github.com/AnthusAI/Biblicus/commit/a28cf3f908b939afe331d3a15f68979366b86847))

- Expand extraction evaluation textbook
  ([`83b6d18`](https://github.com/AnthusAI/Biblicus/commit/83b6d18966be571dee160ca42002f80f41c59039))

- Expand extraction textbook
  ([`db6b8c3`](https://github.com/AnthusAI/Biblicus/commit/db6b8c395898459aafdcc4fdbcbca80396aa02fe))

- Expand knowledge base textbook
  ([`c7412b9`](https://github.com/AnthusAI/Biblicus/commit/c7412b94e706c5b5464c3f5a3c5fc199a7f9fd3f))

- Expand retrieval evaluation textbook
  ([`df4689c`](https://github.com/AnthusAI/Biblicus/commit/df4689c848699bca88755a593a5a8744db0d5c71))

- Expand user configuration and testing textbook
  ([`374743c`](https://github.com/AnthusAI/Biblicus/commit/374743ca87587d972379155fc92b40ece48177b6))

- Link demos to textbook chapters
  ([`dacd105`](https://github.com/AnthusAI/Biblicus/commit/dacd105360020ac97f6c87f9c2cf5fb4883420ee))

- Refresh roadmap for completed analysis
  ([`7176f47`](https://github.com/AnthusAI/Biblicus/commit/7176f4795872c09901a04500f5e7fe65c3e56347))

### Features

- Add ai api multiplexer with provider-agnostic llm and embeddings support
  ([`66de0dc`](https://github.com/AnthusAI/Biblicus/commit/66de0dcd646d5dfb72dac01e492e94ac67261bab))

- Add markov analysis and text utilities
  ([`fd46b2a`](https://github.com/AnthusAI/Biblicus/commit/fd46b2a326253af6f9bcf2113f561c4da9f330cd))

- Add profiling recipes and override handling docs/tests
  ([`56c3302`](https://github.com/AnthusAI/Biblicus/commit/56c33024a2212080eb438f74f82ccf2bba398f13))

- Align biblicus AI stack with DSPy
  ([`cf7a0e2`](https://github.com/AnthusAI/Biblicus/commit/cf7a0e25efb5036ed872cc0b069977e9f262df0c))

Unifies embeddings and completions on DSPy primitives and adds BDD coverage for DSPy-backed Markov
  analysis paths.

- **text**: Text utilities based on a virtual-file-editing paradigm.
  ([`83ae432`](https://github.com/AnthusAI/Biblicus/commit/83ae432f3443b2d01d96450284bfb45340a9023e))


## v0.14.0 (2026-01-30)

### Bug Fixes

- Expand hybrid candidate budgets
  ([`264e27e`](https://github.com/AnthusAI/Biblicus/commit/264e27e39b33476c008c2dcc89640759142b27df))

### Features

- Add retrieval evaluation lab
  ([`2156a93`](https://github.com/AnthusAI/Biblicus/commit/2156a9366320343116b1dc930f97a14747813868))


## v0.13.0 (2026-01-30)

### Documentation

- Add extraction evaluation guide
  ([`857ebe0`](https://github.com/AnthusAI/Biblicus/commit/857ebe0b30d31b296d9c7b296792f3372db9bc01))

- Add extraction evaluation lab walkthrough
  ([`da1c6ce`](https://github.com/AnthusAI/Biblicus/commit/da1c6ce7b4bb3cbca96b2c70a6dedca4da91d11b))

- Add vector backend reference
  ([`12e2793`](https://github.com/AnthusAI/Biblicus/commit/12e27938f9e6bf4e5a3bb347420abd3e1e4032a0))

### Features

- Add extraction evaluation demo
  ([`a7c3efd`](https://github.com/AnthusAI/Biblicus/commit/a7c3efd7da65b3d202e7a518e2fa2bd43774a53e))

- Add extraction evaluation harness
  ([`cc94e90`](https://github.com/AnthusAI/Biblicus/commit/cc94e90f723a54f50202df7f5661dc9b6230d553))

- Add extraction evaluation lab
  ([`8306c8d`](https://github.com/AnthusAI/Biblicus/commit/8306c8de2f459884874b2533df922a30ebd72c23))


## v0.12.0 (2026-01-30)

### Documentation

- Clarify retrieval quality scope
  ([`17ddac5`](https://github.com/AnthusAI/Biblicus/commit/17ddac59287de8dc6c9bfe0f9b970e826330ea8b))

- Update roadmap status for retrieval and context packs
  ([`defac5e`](https://github.com/AnthusAI/Biblicus/commit/defac5ef91260edf83e88936799ec04556aecbaf))

### Features

- Expand context pack policy controls
  ([`9f2b39f`](https://github.com/AnthusAI/Biblicus/commit/9f2b39f662f92fdb65f9bee160fe60b7b226dce1))


## v0.11.0 (2026-01-30)

### Bug Fixes

- Expand hybrid component budgets
  ([`c1122dd`](https://github.com/AnthusAI/Biblicus/commit/c1122dd62bacf744c7a2cd9f92205649e0abca2c))

### Documentation

- Add retrieval evaluation guide
  ([`2b3d294`](https://github.com/AnthusAI/Biblicus/commit/2b3d294bc35ce04a8cc5f997924d086c44c9b0a6))

- Shift retrieval docs to present tense
  ([`6bacf03`](https://github.com/AnthusAI/Biblicus/commit/6bacf03f4d9be5bb5693bcf946f7e08677cb6aac))

### Features

- Add retrieval quality backends and specs
  ([`5e3fbe7`](https://github.com/AnthusAI/Biblicus/commit/5e3fbe78374f8ad006499991dac3e50a029be166))


## v0.10.0 (2026-01-30)


## v0.9.0 (2026-01-30)

### Features

- Add profiling analysis backend
  ([`cac66c9`](https://github.com/AnthusAI/Biblicus/commit/cac66c97cac72c964c0bc2f5e664f87566a5fcd5))


## v0.8.0 (2026-01-30)

### Bug Fixes

- Aggregate all warnings from topic modeling pipeline stages
  ([`15fba05`](https://github.com/AnthusAI/Biblicus/commit/15fba05ebb4a45f1bf2114cd7ac5c2c42b6afe8b))

Collect warnings from all pipeline stages (text, LLM extraction, BERTopic, and fine-tuning) instead
  of just the text stage.

- Correct smart override selection logic for confidence filtering
  ([`bf7f349`](https://github.com/AnthusAI/Biblicus/commit/bf7f349ea7cf8d771ffe232624bc732ea6c21498))

Fix SelectSmartOverrideExtractor to skip extractions with confidence below threshold before checking
  meaningfulness. Ensures high-confidence extractions are preferred over those with missing or low
  confidence.

- Select highest confidence candidate when last extraction is not meaningful
  ([`b2abacf`](https://github.com/AnthusAI/Biblicus/commit/b2abacf0150d63b5b42691910de89642f7cc7e08))

When the last extraction lacks meaningful content, iterate through all previous candidates and
  select the one with the highest confidence score, preferring explicit confidence over missing
  confidence.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

### Documentation

- Document semantic release automation policy
  ([`1682741`](https://github.com/AnthusAI/Biblicus/commit/1682741c596430a42fd2a3be694321d8bb0ce7c9))

Add section to AGENTS.md clarifying that semantic versioning, changelog generation, and PyPI
  publishing are fully automated in GitHub Actions and should not be handled locally.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Update documentation for new features
  ([`2018f88`](https://github.com/AnthusAI/Biblicus/commit/2018f88df12358ad27ab8770348072222b30a4f6))

Update API documentation, extraction guide, user configuration, and README to reflect new
  extractors, analysis pipelines, and inference backends.

### Features

- Add analysis pipeline infrastructure
  ([`d740823`](https://github.com/AnthusAI/Biblicus/commit/d740823bfcc35f616f3582e296f77e4714f3d1b1))

Add base analysis pipeline framework with support for LLM-driven extraction and topic modeling.
  Includes schema validation and model abstractions.

- Add analysis run support to corpus
  ([`d341c28`](https://github.com/AnthusAI/Biblicus/commit/d341c2830240e89cec6b86c84e9df83ff7636dee))

Add analysis_runs_dir property and analysis_run_dir method. Add latest_extraction_run_reference
  helper for retrieving the most recent extraction run.

- Add analysis schema constants
  ([`372d427`](https://github.com/AnthusAI/Biblicus/commit/372d4277ec4ea9a7829ff17220dc78315ac52543))

Add ANALYSIS_SCHEMA_VERSION and ANALYSIS_RUNS_DIR_NAME constants needed by the analysis pipeline
  infrastructure.

- Add BERTopic analysis pipeline
  ([`3e146b0`](https://github.com/AnthusAI/Biblicus/commit/3e146b0c4c98a9338b0be86c90942ab789628386))

- Add confidence scores to extraction output
  ([`e3ac910`](https://github.com/AnthusAI/Biblicus/commit/e3ac9103c11fc30e25d6197435cf50683af725f0))

Add optional confidence field (0.0-1.0) to ExtractedText and ExtractionStepOutput models to support
  extraction quality signals.

- Add extraction pipeline selection utilities
  ([`cec306f`](https://github.com/AnthusAI/Biblicus/commit/cec306f84f98dbb3109b19fc12b330a1e06ca925))

Add SelectOverride and SelectSmartOverride extractors for intelligent extraction result selection in
  pipelines. Allows choosing extraction results based on media type or quality heuristics.

- Add inference backend abstraction
  ([`4de0103`](https://github.com/AnthusAI/Biblicus/commit/4de010319e0337ada792a4c665948c2b52f0d6c3))

Add composable inference backend configuration for components that support both local and API-based
  execution modes. Supports HuggingFace and OpenAI providers.

- Add provider configurations and extractor enhancements
  ([`ac86e6e`](https://github.com/AnthusAI/Biblicus/commit/ac86e6eacf6c30ae694cf2341c64565fef1dd448))

Add Deepgram and HuggingFace user configuration support. Update extractors with confidence score
  support and refined implementations for Docling, PaddleOCR, RapidOCR, and selection utilities.

- Add topic modeling analysis command and recipe file support
  ([`6a60f57`](https://github.com/AnthusAI/Biblicus/commit/6a60f576eb0b5e250df7d4fcaa0beceac6c301dd))

Add biblicus analyze topics command with recipe file support. Improve step spec parsing to handle
  nested structures (braces, brackets) in extraction pipeline configurations.

- Propagate confidence scores through extraction pipeline
  ([`1616d45`](https://github.com/AnthusAI/Biblicus/commit/1616d45d436cfe00c2b40738a49ea25dedc04693))

Thread confidence scores from ExtractedText through ExtractionStepResult to support extraction
  quality signals in the pipeline.

- Register new extractors in factory
  ([`18c0280`](https://github.com/AnthusAI/Biblicus/commit/18c0280bc4bc04b1238f170d8d9e8d5c559c9b02))

Register PaddleOCR, Docling, Deepgram, and selection utility extractors in the extractor factory.

### Testing

- Add feature specs and steps for inference and selection utilities
  ([`84205c3`](https://github.com/AnthusAI/Biblicus/commit/84205c30bcd9a1875f7474629fca6d4ea59dbb5a))

Add BDD feature specifications and step implementations for inference backend configuration and
  extraction result selection utilities.

- Add feature specs for analysis pipelines
  ([`c98cded`](https://github.com/AnthusAI/Biblicus/commit/c98cdedfbd8d8df3effb4920d66f63c55f7a05ac))

Add BDD specifications for analysis pipeline infrastructure including topic modeling analysis and
  schema validation.

- Update feature specs and test steps for new features
  ([`636bd86`](https://github.com/AnthusAI/Biblicus/commit/636bd8653be925f4c00c76311031552fb57e004e))

Update test environment, step implementations, and test fixtures to support new extractors, analysis
  pipelines, inference backends, and configuration options.


## v0.7.0 (2026-01-29)

### Bug Fixes

- Correct import formatting in Docling extractors
  ([`090523d`](https://github.com/AnthusAI/Biblicus/commit/090523d5f4911d8993aae0efe8083fc939a314c9))

Fix Ruff I001 linting errors by properly organizing imports in both Docling VLM extractors.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Enforce 100% coverage gate
  ([`3495377`](https://github.com/AnthusAI/Biblicus/commit/34953770ec9da9db8521a046b5b101e1bee8b86f))

- Stabilize markitdown version guard test
  ([`886fc1c`](https://github.com/AnthusAI/Biblicus/commit/886fc1ced92787e5ca9a6d9053085c5c8070abaf))

### Features

- Add Deepgram speech-to-text extractor
  ([`515a3e8`](https://github.com/AnthusAI/Biblicus/commit/515a3e852c22cc58ff0943db8e04abb4640fa03a))

Add speech-to-text transcription support using Deepgram API. Includes extractor implementation,
  feature tests, and step definitions.

- Add Docling vision-language model extractors
  ([`7f51f49`](https://github.com/AnthusAI/Biblicus/commit/7f51f4941afb0dec312a9ca54c311d44ffa52b20))

Add SmolDocling-256M and Granite Docling-258M vision-language model extractors for document
  understanding. Includes feature tests and step definitions.

- Add MarkItDown extractor
  ([`2a489d6`](https://github.com/AnthusAI/Biblicus/commit/2a489d66fe769b0926e87b05ce40f268c521fc0f))

- Add PaddleOCR vision-language extractor
  ([`4703e76`](https://github.com/AnthusAI/Biblicus/commit/4703e76aa6f73efa6e16834c2921bdb085fdcd38))

Add support for advanced optical character recognition with PaddleOCR vision-language model.
  Includes extractor implementation, feature tests, and unit tests for parsing API responses.


## v0.6.0 (2026-01-29)

### Features

- Knowledge base workflow
  ([`ede4d54`](https://github.com/AnthusAI/Biblicus/commit/ede4d5479ffea62c472c44dc4b51a7b20616f2b8))


## v0.5.0 (2026-01-29)

### Features

- Retrieval evidence pipeline
  ([`593de79`](https://github.com/AnthusAI/Biblicus/commit/593de79589dbc899ba0cd8775b061cafcd36ce36))


## v0.4.0 (2026-01-29)

### Features

- **corpus**: Add crawl and extraction run lifecycle
  ([`0727c08`](https://github.com/AnthusAI/Biblicus/commit/0727c0807705f5483aa1cd87a25e31314eb93a6d))

Add a website crawl workflow with allowed-prefix enforcement and .biblicusignore filtering.\n\nAdd
  extraction run lifecycle commands (build, list, show, delete) with deterministic, idempotent run
  identifiers and inspectable run manifests.\n\nUpdate documentation and roadmap toward retrieval
  MVP.


## v0.3.0 (2026-01-29)

### Bug Fixes

- **stt**: Handle missing optional OpenAI dependency at runtime
  ([`8019f18`](https://github.com/AnthusAI/Biblicus/commit/8019f18bcf966c9a35c5ce894ca462fae4f042ee))

### Chores

- **ci**: Build documentation
  ([`c2690be`](https://github.com/AnthusAI/Biblicus/commit/c2690be862621bb8e7334090bff877c57b122284))

Build Sphinx documentation in continuous integration and release workflows and upload the Hypertext
  Markup Language output as an artifact.

- **ci**: Deploy docs via CI
  ([`57e8062`](https://github.com/AnthusAI/Biblicus/commit/57e8062f5b69d3851879957c58cd1bce8ce9ed9c))

Deploy Sphinx documentation to GitHub Pages only after continuous integration succeeds on main.

- **ci**: Publish documentation site
  ([`123d52a`](https://github.com/AnthusAI/Biblicus/commit/123d52a9b3b2d341bd60a3c90f5e12902886673c))

Publish Sphinx Hypertext Markup Language documentation to GitHub Pages from the main branch.

### Documentation

- Add roadmap and feature index
  ([`17f3f4b`](https://github.com/AnthusAI/Biblicus/commit/17f3f4ba5f72701981ce272339d26abe99660a7b))

Add a conventional roadmap and a feature index that maps behavior specifications to documentation
  and implementation modules.

Refocus next steps on runnable examples and rename corpus workflow notes to a stable design
  document.

### Features

- **extraction**: Add pluggable extraction pipeline
  ([`b7bc0e7`](https://github.com/AnthusAI/Biblicus/commit/b7bc0e78332f4036f6f543704896b61d7892199b))

Adds extraction runs with per-step artifacts and selection policies (select-text,
  select-longest-text).

Includes optional extractors for PDF text (pdf-text), OCR (ocr-rapidocr), speech-to-text
  (stt-openai), and Unstructured catchall, with user configuration support.

Adds integration corpus download scripts and gated integration test flags, plus updated docs, demos,
  roadmap, and CI docs publishing.


## v0.2.0 (2026-01-28)

### Chores

- Add continuous integration and coverage badges
  ([`92c16d2`](https://github.com/AnthusAI/Biblicus/commit/92c16d28cbd993d8e39dfcc962c05e69700fcf5d))

- Update coverage badge
  ([`217b85f`](https://github.com/AnthusAI/Biblicus/commit/217b85fa663873732c581dd013fb038bd4f1c4dd))

### Documentation

- Add diagram legend for region styles
  ([`defac87`](https://github.com/AnthusAI/Biblicus/commit/defac87c53e0fa09c20da463379137b3d52c19aa))

- Add Mermaid diagrams for corpus and retrieval flow
  ([`5527e45`](https://github.com/AnthusAI/Biblicus/commit/5527e4536fea70efdb55464a6f0032915cd18114))

- Add next steps menu and runnable examples
  ([`c5f9e0b`](https://github.com/AnthusAI/Biblicus/commit/c5f9e0b0c572f8e7c2fa852c703e0e547c9e1dba))

- Clean up readme diagram container styling
  ([`f63ad5d`](https://github.com/AnthusAI/Biblicus/commit/f63ad5db1cb3a015d284961453128ced50b630c8))

- Highlight pluggable regions in readme diagram
  ([`7d3d846`](https://github.com/AnthusAI/Biblicus/commit/7d3d84628ac6c3c0029b227f7cbb04fd56b4b1c9))

- Improve diagram legend labels
  ([`7512e45`](https://github.com/AnthusAI/Biblicus/commit/7512e4551864347f420f4af2961431acaa00e1d0))

- Label your code region in readme diagram
  ([`3ce0347`](https://github.com/AnthusAI/Biblicus/commit/3ce0347f51ab97ae9c4f395da22fe0fbf8694416))

- Make readme Mermaid diagram vertical
  ([`0d8f7bf`](https://github.com/AnthusAI/Biblicus/commit/0d8f7bf59b8a988a15eba185005ffa921a36894f))

- Move diagram legend back to left
  ([`68a5b14`](https://github.com/AnthusAI/Biblicus/commit/68a5b14c794e7e342076b0c71a4d8ffcd28827ac))

- Simplify pluggable region diagram
  ([`6c86452`](https://github.com/AnthusAI/Biblicus/commit/6c86452041e536a42ac7e5369a99140c454b1de3))

- Tighten readme Mermaid layout
  ([`66b2d34`](https://github.com/AnthusAI/Biblicus/commit/66b2d34000c998cfa02da0049fa39f3631735101))

### Features

- Add corpus workflows and extraction pipeline
  ([`c9e4b6d`](https://github.com/AnthusAI/Biblicus/commit/c9e4b6d20ea8d3177cce56d57c6ae9286251f055))

Add practical corpus ingestion and management features (ingest sources, streaming ingest, import
  tree, ignore rules, and lifecycle hooks).

Add a text extraction stage with extraction runs, composable extractors (pass-through-text,
  metadata-text), and a cascade pipeline.

Add Portable Document Format sample downloads, integration test selection via scripts/test.py
  --integration, and dedicated documentation pages.


## v0.1.1 (2026-01-27)

### Bug Fixes

- Publish to Python Package Index from release workflow
  ([`de51437`](https://github.com/AnthusAI/Biblicus/commit/de51437472622f8ee3d1e9e404a30fc00944e098))

### Chores

- Publish distributions to Python Package Index
  ([`0973ac6`](https://github.com/AnthusAI/Biblicus/commit/0973ac692e4867b0fdbf88de37c1850e81aac125))


## v0.1.0 (2026-01-27)

### Chores

- Add continuous integration and semantic release
  ([`e921f8d`](https://github.com/AnthusAI/Biblicus/commit/e921f8d0add66ee21210b0533f2434d2f36588ad))

- Fix release publish token and branch checkout
  ([`8491b3b`](https://github.com/AnthusAI/Biblicus/commit/8491b3b09236f1d678efdcef33806c5da7cbe34e))

- Fix semantic release build command
  ([`f748e5d`](https://github.com/AnthusAI/Biblicus/commit/f748e5d37fa8a72efe705862e070df9e0fa0694b))

- Gate release on continuous integration success
  ([`ebebf7f`](https://github.com/AnthusAI/Biblicus/commit/ebebf7f77e45ea39fdbfcd70ece539cdec06982c))

### Features

- Document Python Package Index install
  ([`60ed96d`](https://github.com/AnthusAI/Biblicus/commit/60ed96d06ec7d99448d1ef695f09016689a88f91))

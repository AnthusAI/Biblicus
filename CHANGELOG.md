# CHANGELOG


## v0.9.0 (2026-01-30)


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

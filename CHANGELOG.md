# CHANGELOG


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

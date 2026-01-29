# Biblicus

![Continuous integration][continuous-integration-badge]
![Coverage][coverage-badge]
![Documentation][documentation-badge]

Make your documents usable by your assistant, then decide later how you will search and retrieve them.

If you are building an assistant in Python, you probably have material you want it to use: notes, documents, web pages, and reference files. A common approach is retrieval augmented generation, where a system retrieves relevant material and uses it as evidence when generating a response.

The first practical problem is not retrieval. It is collection and care. You need a stable place to put raw items, you need a small amount of metadata so you can find them again, and you need a way to evolve your retrieval approach over time without rewriting ingestion.

This library gives you a corpus, which is a normal folder on disk. It stores each ingested item as a file, with optional metadata stored next to it. You can open and inspect the raw files directly. Any derived catalog or index can be rebuilt from the raw corpus.

It can be used alongside LangChain, Tactus, Pydantic AI, or the agent development kit. Use it from Python or from the command line interface.

See [retrieval augmented generation overview] for a short introduction to the idea.

## A beginner friendly mental model

Think in three stages.

- Ingest puts raw items into a corpus. This is file first and human inspectable.
- Extract turns items into usable text. This is where you would do text extraction from Portable Document Format files, optical character recognition for images, or speech to text for audio. If an item is already text, extraction can simply read it. Extraction outputs are derived artifacts, not edits to the raw files.
- Retrieve searches extracted text and returns evidence. Evidence is structured so you can turn it into context for your model call in whatever way your project prefers.

If you learn a few project words, the rest of the system becomes predictable.

- Corpus is the folder that holds raw items and their metadata.
- Item is the raw bytes plus optional metadata and source information.
- Catalog is the rebuildable index of the corpus.
- Extraction run is a recorded extraction build that produces text artifacts.
- Backend is a pluggable retrieval implementation.
- Run is a recorded retrieval build for a corpus.
- Evidence is what retrieval returns, with identifiers and source information.

## Diagram

This diagram shows how a corpus becomes evidence for an assistant.
Extraction is introduced here as a separate stage so you can swap extraction approaches without changing the raw corpus.
The legend shows what the block styles mean.
Your code is where you decide how to turn evidence into context and how to call a model.

```mermaid
%%{init: {"flowchart": {"useMaxWidth": true, "nodeSpacing": 18, "rankSpacing": 22}}}%%
flowchart LR
  subgraph Legend[Legend]
    direction LR
    LegendArtifact[Stored artifact or evidence]
    LegendStep[Step]
    LegendStable[Stable region]
    LegendPluggable[Pluggable region]
    LegendArtifact --- LegendStep
    LegendStable --- LegendPluggable
  end

  subgraph Main[" "]
    direction TB

    subgraph StableCore[Stable core]
      direction TB
      Source[Source items] --> Ingest[Ingest]
      Ingest --> Raw[Raw item files]
      Raw --> Catalog[Catalog file]
    end

    subgraph PluggableExtractionPipeline[Pluggable extraction pipeline]
      direction TB
      Catalog --> Extract[Extract pipeline]
      Extract --> ExtractedText[Extracted text artifacts]
      ExtractedText --> ExtractionRun[Extraction run manifest]
    end

    subgraph PluggableRetrievalBackend[Pluggable retrieval backend]
      direction LR

      subgraph BackendIngestionIndexing[Ingestion and indexing]
        direction TB
        ExtractionRun --> Build[Build run]
        Build --> BackendIndex[Backend index]
        BackendIndex --> Run[Run manifest]
      end

      subgraph BackendRetrievalGeneration[Retrieval and generation]
        direction TB
        Run --> Query[Query]
        Query --> Evidence[Evidence]
      end
    end

    Evidence --> Context

    subgraph YourCode[Your code]
      direction TB
      Context[Assistant context] --> Model[Large language model call]
      Model --> Answer[Answer]
    end

    style StableCore fill:#ffffff,stroke:#8e24aa,stroke-width:2px,color:#111111
    style PluggableExtractionPipeline fill:#ffffff,stroke:#5e35b1,stroke-dasharray:6 3,stroke-width:2px,color:#111111
    style PluggableRetrievalBackend fill:#ffffff,stroke:#1e88e5,stroke-dasharray:6 3,stroke-width:2px,color:#111111
    style YourCode fill:#ffffff,stroke:#d81b60,stroke-width:2px,color:#111111
    style BackendIngestionIndexing fill:#ffffff,stroke:#cfd8dc,color:#111111
    style BackendRetrievalGeneration fill:#ffffff,stroke:#cfd8dc,color:#111111

    style Raw fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Catalog fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style ExtractedText fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style ExtractionRun fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style BackendIndex fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Run fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Evidence fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Context fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Answer fill:#f3e5f5,stroke:#8e24aa,color:#111111
    style Source fill:#f3e5f5,stroke:#8e24aa,color:#111111

    style Ingest fill:#eceff1,stroke:#90a4ae,color:#111111
    style Extract fill:#eceff1,stroke:#90a4ae,color:#111111
    style Build fill:#eceff1,stroke:#90a4ae,color:#111111
    style Query fill:#eceff1,stroke:#90a4ae,color:#111111
    style Model fill:#eceff1,stroke:#90a4ae,color:#111111
  end

  style Legend fill:#ffffff,stroke:#ffffff,color:#111111
  style Main fill:#ffffff,stroke:#ffffff,color:#111111
  style LegendArtifact fill:#f3e5f5,stroke:#8e24aa,color:#111111
  style LegendStep fill:#eceff1,stroke:#90a4ae,color:#111111
  style LegendStable fill:#ffffff,stroke:#8e24aa,stroke-width:2px,color:#111111
  style LegendPluggable fill:#ffffff,stroke:#1e88e5,stroke-dasharray:6 3,stroke-width:2px,color:#111111
```

## Practical value

- You can ingest raw material once, then try many retrieval approaches over time.
- You can keep raw files readable and portable, without locking your data inside a database.
- You can evaluate retrieval runs against shared datasets and compare backends using the same corpus.

## Typical flow

- Initialize a corpus folder.
- Ingest items from file paths, web addresses, or text input.
- Run extraction when you want derived text artifacts from non-text sources.
- Reindex to refresh the catalog after edits.
- Build a retrieval run with a backend.
- Query the run to collect evidence and evaluate it with datasets.

## Install

This repository is a working Python package. Install it into a virtual environment from the repository root.

```
python3 -m pip install -e .
```

After the first release, you can install it from Python Package Index.

```
python3 -m pip install biblicus
```

### Optional extras

Some extractors are optional so the base install stays small.

- Optical character recognition for images: `python3 -m pip install "biblicus[ocr]"`
- Speech to text transcription: `python3 -m pip install "biblicus[openai]"` (requires an OpenAI API key in `~/.biblicus/config.yml` or `./.biblicus/config.yml`)
- Broad document parsing fallback: `python3 -m pip install "biblicus[unstructured]"`

## Quick start

```
mkdir -p notes
echo "A small file note" > notes/example.txt

biblicus init corpora/example
biblicus ingest --corpus corpora/example notes/example.txt
echo "A short note" | biblicus ingest --corpus corpora/example --stdin --title "First note"
biblicus list --corpus corpora/example
biblicus extract --corpus corpora/example --step pass-through-text --step metadata-text
biblicus build --corpus corpora/example --backend scan
biblicus query --corpus corpora/example --query "note"
```

## Python usage

From Python, the same flow is available through the Corpus class and backend interfaces. The public surface area is small on purpose.

- Create a corpus with `Corpus.init` or open one with `Corpus.open`.
- Ingest notes with `Corpus.ingest_note`.
- Ingest files or web addresses with `Corpus.ingest_source`.
- List items with `Corpus.list_items`.
- Build a retrieval run with `get_backend` and `backend.build_run`.
- Query a run with `backend.query`.
- Evaluate with `evaluate_run`.

## How it fits into an assistant

In an assistant system, retrieval usually produces context for a model call. This library treats evidence as the primary output so you can decide how to use it.

- Use a corpus as the source of truth for raw items.
- Use a backend run to build any derived artifacts needed for retrieval.
- Use queries to obtain evidence objects.
- Convert evidence into the format your framework expects, such as message content, tool output, or citations.

## Learn more

Full documentation is available on [ReadTheDocs](https://biblicus.readthedocs.io/).

The documents below are written to be read in order.

- [Architecture][architecture]
- [Roadmap][roadmap]
- [Feature index][feature-index]
- [Corpus][corpus]
- [Text extraction][text-extraction]
- [User configuration][user-configuration]
- [Backends][backends]
- [Demos][demos]
- [Testing][testing]

## Metadata and catalog

Raw items are stored as files in the corpus raw directory. Metadata can live in a Markdown front matter block or a sidecar file with the suffix `.biblicus.yml`. The catalog lives in `.biblicus/catalog.json` and can be rebuilt at any time with `biblicus reindex`.

## Corpus layout

```
corpus/
  raw/
    item.bin
    item.bin.biblicus.yml
  .biblicus/
    config.json
    catalog.json
    runs/
      run-id.json
```

## Retrieval backends

Two backends are included.

- `scan` is a minimal baseline that scans raw items directly.
- `sqlite-full-text-search` is a practical baseline that builds a full text search index in Sqlite.

## Integration corpus and evaluation dataset

Use `scripts/download_wikipedia.py` to download a small integration corpus from Wikipedia when running tests or demos. The repository does not include that content.

The dataset file `datasets/wikipedia_mini.json` provides a small evaluation set that matches the integration corpus.

Use `scripts/download_pdf_samples.py` to download a small Portable Document Format integration corpus when running tests or demos. The repository does not include that content.

## Tests and coverage

```
python3 scripts/test.py
```

To include integration scenarios that download public test data at runtime, run this command.

```
python3 scripts/test.py --integration
```

## Releases

Releases are automated from the main branch using semantic versioning and conventional commit messages.

The release pipeline publishes a GitHub release and uploads the package to Python Package Index when continuous integration succeeds.

Publishing uses a Python Package Index token stored in the GitHub secret named PYPI_TOKEN.

## Documentation

Reference documentation is generated from Sphinx style docstrings.

Install development dependencies:

```
python3 -m pip install -e ".[dev]"
```

Build the documentation:

```
python3 -m sphinx -b html docs docs/_build
```

## License

License terms are in `LICENSE`.

[retrieval augmented generation overview]: https://en.wikipedia.org/wiki/Retrieval-augmented_generation
[architecture]: docs/ARCHITECTURE.md
[roadmap]: docs/ROADMAP.md
[feature-index]: docs/FEATURE_INDEX.md
[corpus]: docs/CORPUS.md
[text-extraction]: docs/EXTRACTION.md
[user-configuration]: docs/USER_CONFIGURATION.md
[backends]: docs/BACKENDS.md
[demos]: docs/DEMOS.md
[testing]: docs/TESTING.md

[continuous-integration-badge]: https://github.com/AnthusAI/Biblicus/actions/workflows/ci.yml/badge.svg?branch=main
[coverage-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AnthusAI/Biblicus/main/coverage_badge.json
[documentation-badge]: https://readthedocs.org/projects/biblicus/badge/?version=latest

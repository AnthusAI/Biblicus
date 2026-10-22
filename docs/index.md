# Biblicus

![Biblicus logo](images/Biblicus-logo.png)

You have a big collection of files. You need answers about what is in it, and you want to be able to show it to an AI agent to talk about it.

Biblicus is a Python toolkit that turns unstructured data into something you can manage, search, analyze, and reuse. It supports end-to-end pipelines: ingest and extract content from mixed file types, transform text with reusable AI utilities, retrieve evidence into model-friendly context, and evaluate results so improvements are measurable.

Common, believable scenarios look like this:

- You inherit a huge archive of emails and need to build an assistant that can answer questions while protecting sensitive details.
- You receive a legal discovery dump of scanned PDFs and need to search, summarize, and trace evidence across thousands of pages.
- You need to make a policy or rules folder usable inside an AI system even though the source materials are far larger than any model context window.

If you have ever built a one-off script to "just get this data into shape", Biblicus is the version of that work you can keep: structured, repeatable, and designed for experimentation.

The project emphasizes evidence-first results, explicit retrieval stages, and evaluation so you can defend what was retrieved, from where, and why.

Looking for the Python API? The [API reference](api-reference/api.html) is generated from the package docstrings.

## Try It

If you want to decide quickly whether Biblicus is useful, run a tutorial. Each tutorial is a small script that produces concrete output, and each one is covered by behavior specs so we do not publish "works on my machine" examples.

Three good starting points:

**Notes to context**

Take a handful of short notes and turn them into a token-budgeted context pack you can paste into a model request.

See [Notes to Context Pack](use_cases/notes_to_context_pack.md).

```bash
python scripts/use_cases/notes_to_context_pack_demo.py \
  --corpus corpora/tutorial_notes_to_context_pack \
  --force
```

**Folder search**

Ingest a folder of text files, build a deterministic index, and retrieve evidence with provenance.

See [Folder Search With Extraction](use_cases/text_folder_search.md).

```bash
python scripts/use_cases/text_folder_search_demo.py \
  --corpus corpora/tutorial_text_folder_search \
  --force
```

**Sensitive text marking (mock + real API)**

Mark sensitive spans in a document using an agentic text utility. Run it in deterministic mock mode first, then switch to a real model when you are ready.

See [Mark Sensitive Text for Redaction](use_cases/text_redact.md).

```bash
python scripts/use_cases/text_redact_demo.py \
  --corpus corpora/tutorial_text_redact \
  --force \
  --mock
```

If your data has an inherent sequence (threads, transcripts, recurring phases), Markov analysis adds a sequence model on top of segmented text. See [Sequence Graph With Markov Analysis](use_cases/sequence_markov.md).

All tutorials: [Use Cases](use-cases.md).

## Learn the Concepts

If you want the mental model before running anything, start with data collections and extraction, then move into retrieval and analysis. The rest of the documentation expands those foundations into deeper evaluation and tooling.

Biblicus uses a small set of domain terms in its docs. The most important one is *corpus* (plural: *corpora*): a managed folder on disk that holds raw items plus lightweight metadata.

- [Corpus](CORPUS.md)
- [Extraction](extraction.md)
- [Retrieval](retrieval.md)
- [Analysis](analysis.md)
- [Graph Extraction](graph-extraction.md)

## Core Building Blocks

These pages define the vocabulary and invariants that keep Biblicus stable across retrievers and configurations. Read them when you want to understand what is a corpus, what is evidence, and what stays the same even when the pipeline changes.

- [Corpus Design](corpus-design.md)
- [Corpus](CORPUS.md)
- [Knowledge Base](knowledge-base.md)
- [Backends](backends.md)
- [Retrieval Backends](backends/index.md)
- [Context Pack](context-pack.md)
- [Context Engine](context-engine.md)

## Extraction and Ingestion

Extraction turns raw files into usable text. Biblicus supports pluggable extractors so you can mix plain text handling with OCR, document parsers, and speech-to-text pipelines.

- [Extraction](extraction.md)
- [Extraction Evaluation](extraction-evaluation.md)
- [Extractors](extractors/index.md)
- [Speech to Text](STT.md)

## Retrieval and Evaluation

Retrieval is how you move from a large corpus to a compact, relevant evidence set. These pages cover baseline retrieval, hybrid strategies, and how to evaluate retrieval quality.

- [Retrieval](retrieval.md)
- [Retrieval Quality](retrieval-quality.md)
- [Retrieval Evaluation](retrieval-evaluation.md)
- [Embedding Retrieval](embedding-retrieval.md)
- [Chunking](CHUNKING.md)

## Analysis and Modeling

Analysis tools help you find structure inside large text corpora. Topic modeling provides a first pass at clustering themes. Topic classifiers turn reviewed exemplars into reusable classifier model versions. Markov analysis (Hidden Markov Models) adds sequence modeling to detect recurring phases in longer documents or conversations.

- [Profiling](PROFILING.md)
- [Topic Modeling](topic-modeling.md)
- [Topic Classifier](topic-classifier.md)
- [Taxonomy and Ontology](taxonomy-ontology.md)
- [Research Agent Intake](research-agent-intake.md)
- [Topic Trends](topic-trends.md)
- [Topic Identity](topic-identity.md)
- [Steering Proposals](steering-proposals.md)
- [Markov Analysis](markov-analysis.md)

## Toolbox

Reusable building blocks support common transformations in information pipelines. They are designed to be simple to invoke while enabling sophisticated behavior under the hood, so you can slot them into ETL-like workflows without building a custom agent every time.

- [Utilities](utilities.md)
- [Text Utilities](text-utilities.md)
- [Entity Removal](entity-removal.md)
- [Text Extract](text-extract.md)
- [Text Slice](text-slice.md)
- [Text Annotate](text-annotate.md)
- [Text Redact](text-redact.md)
- [Text Link](text-link.md)

## Operations and Demos

Operational docs help you run the system, configure it, and reproduce examples. The demo guides are designed to be runnable end-to-end and serve as acceptance tests.

- [Demos](demos.md)
- [User Configuration](user-configuration.md)
- [Steering Integration](steering-integration.md)
- [Testing](TESTING.md)

## Reference

Reference material, design notes, and the API index live here.

- [API reference](api-reference/api.html) (generated with Sphinx from the Python docstrings)
- [Feature Index](feature-index.md)
- [Roadmap](roadmap.md)
- [Architecture](architecture.md)
- [Bounded Web Transform](bounded-web-transform.md)
- [API Contract](api-contract.md)
- [Benchmarking guides](guides/quickstart-benchmarking.md)

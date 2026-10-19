# Biblicus Architecture

Biblicus sits between raw, unstructured data and the moment you need reliable answers from it.
It is built for teams who receive large, messy corpora and must extract usable signals without
losing provenance or reproducibility. Retrieval-augmented generation is one use case, but the
system is broader than chatbots: it supports any pipeline that needs structured insight from
unstructured data.

At a high level the system does five things:

1. **Ingests** raw content into a corpus with minimal friction.
2. **Extracts** text from diverse media (documents, images, audio).
3. **Transforms** and annotates text with reusable LLM utilities.
4. **Retrieves** evidence through explicit, reproducible stages.
5. **Evaluates** results so improvements are measurable, not anecdotal.

The guiding idea is that every retrieval produces **evidence**: structured outputs with scores
and provenance that can be inspected, audited, and reused. Context packs, summaries, and downstream
generation are all derived from that evidence.

## Core Concepts

- **Corpus**: a named, mutable collection rooted at a path or uniform resource identifier. In
  version zero it is typically a local folder containing raw files plus a `metadata/` directory
  for minimal metadata.
- **Item**: the unit of ingestion in a corpus: raw bytes of any modality, including text, images,
  Portable Document Format documents, audio, and video, plus optional metadata and provenance.
- **Knowledge base backend**: an implementation that can ingest and retrieve from a corpus, such
  as scan, full text search, vector retrieval, or hybrid retrieval, exposed to procedures through
  retrieval primitives.
- **Retrieval configuration**: a named configuration bundle for a backend, such as chunking rules,
  embedding model and version, hybrid weights, reranker choice, and filters. This is what we
  benchmark and compare.
- **Configuration manifest**: a reproducibility record describing the backend and configuration parameters,
  plus any referenced snapshot artifacts and build snapshots.
- **Snapshot artifacts**: optional, persisted representations derived from raw content for a given
  configuration and backend, such as chunks, embeddings, or indexes. Some backends intentionally have
  none and operate on demand.
- **Evidence**: structured retrieval output from backend queries. Evidence includes spans, scores,
  and provenance used by downstream retrieval augmented generation procedures.
- **Pipeline stage / editorial layer**: a structured stage that transforms, filters, extracts, or
  curates content, such as raw, curated, and published, or extract text from Portable Document
  Format documents.

## Design Principles

- **Primitives + derived constructs**: keep the protocol surface small and composable; ship
  higher-level helpers and example procedures on top.
- **Composability definition**: composable means each stage has a small input and output contract,
  so you can connect stages in different orders without rewriting them.
- **Minimal opinion raw store**: raw ingestion should work for a folder of files with optional
  lightweight tagging.
- **Reproducibility by default**: comparisons require manifests (even when there are no persisted
  snapshot artifacts).
- **Mutability is real**: corpora are edited, pruned, and reorganized; re-indexing must be a core
  workflow.
- **Separation of concerns**: retrieval returns evidence; retrieval-augmented generation patterns
  live in Tactus procedures (not inside the knowledge base backend).
- **Deployment flexibility**: same interface across local/offline, brokered external services, and
  hybrid environments.
- **Evidence is the primary output**: every retrieval returns structured evidence; everything else
  is a derived helper.

## The Python Developer Mental Model

If this system is pleasant to use, a Python developer should be able to describe intent with the
core nouns:

- I have a **corpus** at this path or uniform resource identifier.
- I ingest an **item** with optional **metadata**.
- I rebuild the derived **index** after edits.
- I run a **configuration** against the same corpus.
- I query and receive **evidence**.

Anything that does not map cleanly to these nouns is either a derived helper or a backend-specific
implementation detail that should not leak.

## Evidence Lifecycle

Evidence flows through explicit stages and remains inspectable at every step:

1. **Retrieval**: backends return evidence with `stage` labels and scores.
2. **Processing**: optional reranking or filtering updates scores while preserving provenance.
3. **Context shaping**: context packs select and format evidence into model-ready text.
4. **Evaluation**: evaluation datasets compare evidence rankings to expectations.

At each stage, the output remains a structured object, so you can inspect, store, and compare
runs without re-running the entire pipeline.

## Relationship to Agent Frameworks

Biblicus integrates with agent frameworks through explicit tool interfaces. It does not hide
retrieval inside the model. Instead, it provides repeatable pipelines that expose *what* was
retrieved and *why*, so models can use evidence directly and safely.

- **Tools and toolsets**, including the Model Context Protocol, are the primary capability
  boundary.
- **Sandboxing and brokered or secretless execution** are primary deployment modes.
- **Durability and evaluations** are central: invariants via specifications, quality via
  evaluations.

## Stability promise for Tactus

Tactus is the first consumer of Biblicus as a library. It declares the requirement
`biblicus>=1.11.3,<2.0.0`, so every release inside major version one reaches Tactus users
automatically. A library that other projects build on must therefore say precisely which names
it will not change without a major version. This section is that statement.

The promise covers the following public names, exactly as Tactus imports them. Within major
version one they keep their import path, their name, and the meaning of their fields and
arguments. New optional fields and new names may be added; existing ones are not removed, renamed,
or given a different meaning.

| Module | Names Tactus depends on |
| --- | --- |
| `biblicus.corpus` | `Corpus` |
| `biblicus.context` | `ContextPack`, `ContextPackBlock` |
| `biblicus.context_engine` | `ContextAssembler`, `ContextAssemblyResult`, `retrieve_context_pack`, `ContextRetrieverRequest`, `BaseCompactor`, `CompactionRequest`, `SummaryCompactor`, `TruncateCompactor`, and the declaration and specification models `AssistantMessageSpec`, `CompactorDeclaration`, `ContextBudgetSpec`, `ContextDeclaration`, `ContextExpansionSpec`, `ContextInsertSpec`, `ContextMessageSpec`, `ContextPackBudgetSpec`, `ContextPackSpec`, `ContextPolicySpec`, `ContextTemplateSpec`, `CorpusDeclaration`, `HistoryInsertSpec`, `RetrieverDeclaration`, `SystemMessageSpec`, `UserMessageSpec` |
| `biblicus.context_engine.compaction` | `build_compactor` |
| `biblicus.workflow` | `build_plan_for_extract`, `build_plan_for_index`, `build_default_handler_registry` |
| `biblicus.ai.models` | `LlmClientConfig` |
| `biblicus.text` | `apply_text_annotate`, `apply_text_extract`, `apply_text_link`, `apply_text_redact`, `apply_text_slice` |
| `biblicus.text.markup` | `parse_span_markup`, `strip_span_tags`, `summarize_span_context` |
| `biblicus.text.models` | `TextAnnotateRequest`, `TextExtractRequest`, `TextLinkRequest`, `TextRedactRequest`, `TextSliceRequest` |

A promise that nothing checks is only a hope, so the release process checks it. Before a release
is created, the workflow `tactus-compatibility.yml` builds a wheel from the commit being
released, checks out the Tactus repository, installs Tactus with its development extras, replaces
the published Biblicus with the candidate wheel, and runs the Tactus tests that exercise the
names above:

- the pytest modules `tests/core/test_retrieval.py`, `tests/core/test_context_assembler.py`,
  `tests/core/test_compaction.py`, `tests/core/test_runtime_tasks.py`,
  `tests/stdlib/test_biblicus_text.py`, and `tests/dspy/test_agent_context_assembly.py`;
- the behave scenarios in `features/*_context_*.feature` and
  `features/90_task_dependency_planning.feature`.

The release job needs this check to succeed, and the publish job needs the release job, so a
failing check creates no version tag, no release notes, and no package on the Python Package
Index. The same check runs on every push and pull request in the continuous integration workflow,
which means a breaking change is normally caught before it is merged. When the check fails, the
fix is one of two things: restore the promised behavior in Biblicus, or, if the change is
intended, make it in a major version and update the Tactus requirement in step.

## Where to go next

- Start with **corpus.md** and **extraction.md** to understand how raw content is ingested.
- Move to **retrieval.md** and **retrieval-evaluation.md** to see how evidence is produced and tested.
- Explore **topic-modeling.md** and **markov-analysis.md** if you need higher-level analysis tools.
- See **text-utilities.md** for reusable, AI-assisted text transformations.

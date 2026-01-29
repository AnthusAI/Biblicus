# Biblicus Architecture

Biblicus is a command line interface first **corpus** manager for ingesting, curating, and evaluating corpora used by assistant systems. The early goal is to make it easy to add raw, unstructured content, while keeping the system structured enough to support reproducible experiments.

## How we design

Design starts from strict behavior-driven development:
- The authoritative description of behavior lives in `features/*.feature`.
- All changes should follow specification-first behavior-driven development: failing scenario, implementation, passing scenario, then refactor.
- Behavior-driven development scenarios are not an afterthought: they are how we keep the domain vocabulary consistent and the platform comparable across backends and recipes.
- **Specification completeness** is mandatory: if behavior exists, it must be specified. Ambiguous or untestable behavior should be removed or turned into an explicit error.

## Domain-specific cognitive framework

The domain-specific cognitive framework is the set of **stable nouns**, **verbs**, and **invariants** that make Biblicus pleasant to use over time.
We prefer a small set of universal concepts with strict semantics over a large set of ad-hoc flags.

We also treat **Pydantic models** as the canonical way to codify and validate these constructs at boundaries.

## The Python developer mental model

If this system is pleasant to use, a Python developer should be able to describe intent with the core nouns:

- I have a **corpus** at this path or uniform resource identifier.
- I ingest an **item** with optional **metadata**.
- I rebuild the derived **index** after edits.
- I run a **recipe** against the same corpus.
- I query and receive **evidence**.

Anything that does not map cleanly to these nouns is either a derived helper or a backend-specific implementation detail that should not leak.

## Relationship to agent frameworks

Biblicus is designed to integrate with agent frameworks through explicit tools and clear application programming interfaces. Tactus is one target environment with strong isolation requirements.

- **Tools and toolsets**, including the Model Context Protocol, are the primary capability boundary.
- **Sandboxing and brokered or secretless execution** are primary deployment modes.
- **Durability and evaluations** are central: invariants via specifications, quality via evaluations.

## Core concepts

### Concepts

- **Corpus**: a named, mutable collection rooted at a path or uniform resource identifier. In version zero it is typically a local folder containing raw files plus a `.biblicus/` directory for minimal metadata.
- **Item**: the unit of ingestion in a corpus: raw bytes of any modality, including text, images, Portable Document Format documents, audio, and video, plus optional metadata and provenance.
- **Knowledge base backend**: an implementation that can ingest and retrieve from a corpus, such as scan, full text search, vector retrieval, or hybrid retrieval, exposed to procedures through retrieval primitives.
- **Retrieval recipe**: a named configuration bundle for a backend, such as chunking rules, embedding model and version, hybrid weights, reranker choice, and filters. This is what we benchmark and compare.
- **Recipe manifest**: a reproducibility record describing the backend and recipe parameters, plus any referenced materializations and build runs.
- **Materialization**: an optional, persisted representation derived from raw content for a given recipe and backend, such as chunks, embeddings, or indexes. Some backends intentionally have none and operate on demand.
- **Evidence**: structured retrieval output from backend queries. Evidence includes spans, scores, and provenance used by downstream retrieval augmented generation procedures.
- **Pipeline stage / editorial layer**: a structured step that transforms, filters, extracts, or curates content, such as raw, curated, and published, or extract text from Portable Document Format documents.

## Design principles

- **Primitives + derived constructs**: keep the protocol surface small and composable; ship higher-level helpers and example procedures on top.
- **Composability definition**: composable means each stage has a small input and output contract, so you can connect stages in different orders without rewriting them.
- **Minimal opinion raw store**: raw ingestion should work for a folder of files with optional lightweight tagging.
- **Reproducibility by default**: comparisons require manifests (even when there are no persisted materializations).
- **Mutability is real**: corpora are edited, pruned, and reorganized; re-indexing must be a core workflow.
- **Separation of concerns**: retrieval returns evidence; retrieval-augmented generation patterns live in Tactus procedures (not inside the knowledge base backend).
- **Deployment flexibility**: same interface across local/offline, brokered external services, and hybrid environments.
- **Evidence is the primary output**: every retrieval returns structured evidence; everything else is a derived helper.

## Locked decisions (version zero)

These are explicit, opinionated policies encoded into the project:

- **Evidence schema strictness**: moderate-to-strong schema. Evidence must include stable identifiers, provenance, and retrieval scores; richer fields (spans, stage, recipe and run identifiers) are expected.
- **Retrieval stages**: multi-stage is explicit (retrieve, rerank, then filter). Pipelines are expressed through evidence metadata rather than hard-coded backends.
- **Corpus versioning**: snapshot or reindex runs are versioned; full directed acyclic graph lineage is deferred.
- **Evaluation datasets**: mixed human-labeled and synthetic questions; human-labeled for truth, synthetic for scale.
- **Baseline retriever**: hybrid is the strategic target, but the first reference backend is deterministic lexical.
- **Context budgeting**: evidence selection is governed by budgets (token, unit, and per-source limits), not a fixed count.

## Evidence schema (version zero)

Evidence is the canonical output of retrieval. Required fields:

- `item_id`, `source_uri`, `media_type`
- `score` and `rank`
- `text` (or `content_ref` when non-text)
- `stage` (for example, `scan`, `full-text-search`, `rerank`)
- `recipe_id` / `run_id` (for reproducibility)
- Optional: `span_start`, `span_end`, `hash`

## Architectural policies version zero

### Integration boundary

- Biblicus can integrate with Tactus as a **Model Context Protocol toolset**, for example with tool names such as `knowledge_base_ingest`, `knowledge_base_query`, and `knowledge_base_stats`.
- We will **not** add a knowledge base or retrieval augmented generation language primitive in version zero. Revisit only if we need semantics that tools cannot express cleanly, such as enforceable policy boundaries, runtime managed durability, caching hooks, or guaranteed instrumentation.

### Interface packaging

- The knowledge base interface is a **small protocol and reference implementation**, including tool schemas and a reference Model Context Protocol server. We will not build a full managed service in version zero.

### Corpus identity and layout

- Corpora are identified by a **uniform resource identifier**; simple strings and paths normalize to canonical `file://...`.
- The raw corpus is the source of truth and must support:
  - a plain folder of arbitrary files
  - optional Markdown + Yet Another Markup Language front matter for lightweight tagging
  - sidecar metadata for any file type (for example, `file.pdf.biblicus.yml`)
- Raw items are written with **usable file extensions** whenever possible (based on `media_type`) so the corpus remains easy to browse and recover with ordinary operating system tools.

### Mutability and editorial workflow

- Corpora are **mutable**. Re-indexing and refresh are primary operations.
- Filtering, pruning, and curation are primary needs; we may model this as a **multi-layer editorial pipeline** such as raw, curated, then published.

### Pipeline stages

- Text extraction (Portable Document Format, office documents, or image optical character recognition) is a **pipeline stage**, not part of raw ingestion.

### Backend hosting modes (all supported)

Biblicus must support all three backend hosting modes behind the same interface, and ship at least one reference example of each:

- **In-process plugin**: simplest local minimum viable product and deterministic testing.
- **Out-of-process local daemon**: isolates dependencies and supports warm indexes for heavier systems.
- **Remote service**: production deployments, multi-tenant separation, and managed infrastructure.

Backend hosting mode is a primary benchmark dimension (cold start, warm start, latency, throughput, cost, operational complexity).

### Security / sandbox topology (all supported)

Biblicus must support all three deployment topologies, selected as appropriate per environment and backend:

- **In-sandbox**: the knowledge base runs inside the Tactus sandbox container (local, offline, simplest wiring).
- **Brokered or external**: the knowledge base runs outside the sandbox and is accessed via tools (aligns with secretless or brokered execution).
- **Hybrid**: mix modes across environments (for example, local development in-sandbox; production external).

The interface stays the same; topology is configuration.

### Query semantics

- `knowledge_base_query` returns **evidence objects** as the low-level, composable building block.
- Biblicus may ship higher-level convenience helpers built on top of evidence (for example, a prompt-ready context pack formatter), but those helpers remain derived and swappable.

### Reproducibility

- Biblicus always records a **recipe manifest** for reproducibility.
- When a backend produces persisted materializations, Biblicus treats them as **versioned build runs** identified by `run_id` (rather than overwriting in place by default).
- Manifests exist even for just-in-time backends (materializations may be empty).
- Full directed acyclic graph lineage is not included in version zero; revisit only if needed.
- Future (optional): define **shared materialization formats** (canonical chunk and embedding stores) so multiple backends can reuse intermediates when it makes sense; keep it opt-in.

### Evaluation

- Evaluate **both** knowledge base level behavior and end-to-end procedure behavior using **shared datasets**:
  - **Knowledge base level**: retrieval metrics and system properties (for example, recall and mean reciprocal rank, latency, index size, and cost).
  - **Procedure-level (Tactus)**: end-to-end success, policy compliance, and quality metrics across real inputs.

### Catalog stance

- The corpus catalog is **file-based** (committable, portable, backend-agnostic) so any backend/tool can consume it without requiring a database engine.
- Canonical version zero format is a single JavaScript Object Notation file at `.biblicus/catalog.json`, written atomically (temporary file and rename) on updates.
- The catalog includes `latest_run_id` and run manifests are stored at `.biblicus/runs/<run_id>.json`.
- If this ever becomes a bottleneck at very large scales, we will **change the specification** (bump `schema_version`) rather than introduce multiple “supported” catalog storage modes.

## Near-term deliverables

1. Define Biblicus version zero knowledge base tool schemas (Model Context Protocol) for:
   - `knowledge_base_ingest` (upsert documents)
   - `knowledge_base_query` (retrieve evidence)
   - `knowledge_base_get` and `knowledge_base_list` (basic management)
   - `knowledge_base_stats` (latency, counts, sizes)
2. Implement reference backend examples for each hosting mode:
   - **In-process plugin**: a naive local backend (for example, metadata registry and lexical baseline) for determinism and tests
   - **Local daemon**: a vector backend (Qdrant or Postgres with pgvector) for real use
   - **Remote service**: the same vector backend configured against a remote endpoint
3. Implement one reference Tactus procedure showing a basic retrieval-augmented generation pattern using the toolset.
4. Add a small evaluation dataset and run `tactus eval` against multiple retrieval configs.

## Open questions

- **Editorial pipeline model**: do layers live as directory views, metadata flags, or both?
- **Chunking strategy**: semantic vs fixed-size, and how to compare fairly across corpora.
- **Re-ranking tradeoffs**: quality versus cost and latency, and when to use cross-encoders.
- **Context synthesis**: raw snippets vs summary-based packs, and how to evaluate hallucination risk.

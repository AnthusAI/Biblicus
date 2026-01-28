# Corpus design

This document records design decisions and outcomes for corpus management and lifecycle hooks in version zero.

The goal is to make corpus management practical for day to day use, while keeping the raw corpus durable and readable as ordinary files on disk.

## What exists today

The project already supports:

- Ingest notes, local files, and web addresses into a corpus folder
- Store each item as a raw file plus optional sidecar metadata
- Detect a suggested filename from a web address path
- Detect a media type from a response header when available, or fall back to a filename based guess
- Rebuild the catalog from the raw corpus at any time

The decisions below describe how version zero refined and extended these workflows without changing the core principle that the corpus is the source of truth.

## Core vocabulary for this document

- Corpus: the folder that holds raw items and their metadata.
- Item: raw bytes plus metadata and provenance.
- Catalog: the rebuildable index of the corpus.
- Backend: a pluggable retrieval implementation.
- Backend index: backend specific derived artifacts created during a run build.
- Pipeline stage: a distinct step that transforms items, catalogs, or evidence.
- Hook: an explicit point in the lifecycle where a plugin can run.

## Day to day corpus workflows

These are the workflows that tend to matter most for a person building a corpus.

- Rapid capture: throw an item into a corpus quickly, with minimal friction.
- Curation: add tags, titles, and small annotations that help later retrieval.
- Bulk import: bring in an existing folder tree or exported archive.
- Hygiene: detect invalid metadata, duplicates, and obviously broken items.
- Reversible pruning: remove items from active use without losing raw source material.
- Auditing: answer what changed, when it changed, and why it changed.

## Decision points with options and recommendations

Each decision point includes a few viable options. These are not mutually exclusive in an absolute sense, but the project policy is one official way, so each section ends with a recommendation.

## Locked decisions

The decisions below are treated as project policy for the hook system, and they are implemented in version zero.

- Hook interfaces are expressed as Python Protocol types or abstract base classes.
- Hook inputs and outputs are Pydantic models.
- Hook execution is recorded as structured log files.
- Invalid hook data is a hard error with a clear message.

### Decision 1: corpus ignore rules

Goal: prevent accidental ingestion of irrelevant files such as build artifacts, large caches, and hidden metadata files.

Option A: a corpus ignore file stored in the corpus root

- Use a single file such as `.biblicusignore` in the corpus root.
- Use a gitignore style pattern language.
- Apply the ignore rules consistently across import and crawl workflows.

Option B: explicit ignore patterns passed to each command

- The command line interface accepts repeated `--ignore` patterns.
- No on disk record unless the user also writes it somewhere.

Option C: a strict allow list instead of ignore patterns

- Only ingest files that match a known allow list.
- Safer, but higher friction.

Recommendation

Pick option A. A corpus should be self describing, and ignore rules are part of the corpus identity. A single ignore file is easy to document, easy to version, and easy to apply in every workflow.

Outcome

Version zero implemented option A with a `.biblicusignore` file in the corpus root.

### Decision 2: large item ingestion and streaming

Goal: support large files and downloads without loading everything into memory.

Option A: keep the current bytes based ingestion only

- Simple, but fails on large items.
- Pushes users to write custom ingestion code.

Option B: add a streaming ingestion path that writes to disk in chunks

- Provide a method that accepts a readable binary stream and writes it incrementally.
- Compute a checksum as it writes.
- Store the checksum in sidecar metadata.

Option C: provide a dedicated download and ingest command that streams

- A command focused on web addresses that streams directly to disk.
- More specialized, but can handle redirects and long responses better.

Recommendation

Pick option B first. The core domain object is the item, and a stream is a natural way to represent large raw bytes. A dedicated download command can be layered on later as a convenience.

Outcome

Version zero implemented option B by adding a streaming ingestion path for local, non markdown files, with checksum recording.

### Decision 3: content aware filename and media type detection

Goal: make raw files easy to open and inspect in a file manager, without guessing what the content is.

Option A: trust the response header and the address path

- Use the response content type header when available.
- Use the address path to infer a filename.
- This was close to the initial behavior.

Option B: use light content sniffing for a small set of common formats

- Detect Portable Document Format, Hypertext Markup Language, plain text, and common image types.
- Prefer sniffed type when the header is missing or obviously wrong.

Option C: require explicit media type and filename in ingest calls

- Most explicit, but high friction, and not practical for rapid capture.

Recommendation

Pick option B. The benefit is daily usability. A user should be able to open a raw file and have the operating system recognize it. Light sniffing can be limited to a few signatures and still deliver most of the value.

Outcome

Version zero implemented option B for a small set of common file types when a web response is generic.

### Decision 4: folder tree import semantics

Goal: import an existing library of files while preserving provenance.

Option A: preserve relative paths in a dedicated imported namespace

- Store raw files under a subfolder such as `raw/imports/<import_id>/...`.
- Record the original relative path in metadata.
- Avoid name collisions.

Option B: flatten everything into the raw folder

- Fast, but loses provenance and increases collision risk.

Option C: store a reference to the original file and do not copy bytes

- Lower storage cost, but not durable if the original location changes.

Recommendation

Pick option A. The corpus should be a stable source of truth. Copying bytes into a dedicated imported namespace preserves provenance while remaining durable.

Outcome

Version zero implemented option A with an `import-tree` command that preserves relative paths under an imports namespace.

### Decision 5: website crawl scope and safety

Goal: ingest a small documentation site or a set of pages under a base address, without turning the tool into a general web crawler.

Option A: a strict base address prefix rule

- Accept a base address and refuse to crawl outside of it.
- Follow links only if they remain under that prefix.

Option B: a host based rule

- Follow any link on the same host.
- Easier, but can drift to unrelated paths.

Option C: no crawler, only single page ingestion

- Lowest complexity, but users must bring their own crawler.

Recommendation

Pick option A. It is simple to explain, easy to test, and safe by default.

Outcome

Version zero locked this as policy. A crawler was not implemented yet.

### Decision 6: editorial workflow and reversible pruning

Goal: remove or hide items from active use without destroying the raw source material.

Option A: a soft delete flag in metadata

- Mark items as inactive in sidecar metadata.
- Retrieval backends can exclude inactive items by default.

Option B: a multi layer corpus concept

- A base corpus plus derived curated views.
- Powerful, but risks complexity early.

Option C: move pruned items to an archive folder

- Preserves bytes and makes pruning obvious in the file system.
- Requires careful catalog rebuild logic.

Recommendation

Pick option A first. It aligns with the catalog model and keeps the raw bytes stable. Option C can be added later as a more explicit physical archive if users want it.

Outcome

Version zero locked this as policy. A prune workflow was not implemented yet.

### Decision 6A: derived artifact storage is partitioned by plugin type

Goal: retain derived artifacts from multiple implementations side by side so a user can compare results and switch between implementations without losing work.

This decision applies to extraction plugins and retrieval backends, and to any future plugin type that produces derived artifacts.

Option A: store artifacts under the corpus, partitioned by plugin type

- Store derived artifacts under the corpus, not in a global cache.
- Partition by plugin type, then by plugin identifier, then by run identifier.
- Keep raw items separate and immutable under the raw directory.

Suggested layout

- `.biblicus/runs/extraction/<extractor_id>/<run_id>/...`
- `.biblicus/runs/retrieval/<backend_id>/<run_id>/...`
- `.biblicus/runs/evaluation/<evaluator_id>/<run_id>/...`

Option B: store artifacts under the corpus but only partition by run identifier

- Store derived artifacts under `.biblicus/runs/<run_id>/...`.
- The run manifest records plugin identifiers and configuration.
- Simple, but it is harder to browse and compare by implementation on disk.

Option C: store artifacts outside the corpus in a workspace cache

- Keep the corpus folder free of derived artifacts.
- Store artifacts under a user specific cache path.
- This makes portability and disaster recovery harder and does not match the project goal of a corpus that can be backed up as a folder.

Recommendation

Pick option A. It supports the comparison workflow directly and it makes the corpus folder a complete, portable unit for experimentation. The raw directory remains the source of truth, and derived artifacts remain clearly separated and rebuildable.

Outcome

This was partially implemented in the current system. Extraction runs are stored under the corpus, partitioned by plugin type and extractor identifier. Retrieval runs are still stored under a single runs directory without backend partitioning.

### Decision 6B: extraction is a separate plugin stage from retrieval

Goal: support experimentation where an extraction implementation and a retrieval implementation can be swapped independently while using the same corpus.

This decision was driven by optical character recognition, but it applies to any extraction method that converts source items into derived text artifacts.

Option A: extraction is embedded in the retrieval backend

- Retrieval backends run extraction during build.
- Simple to implement in a single backend, but it prevents systematic comparison across extraction providers.
- It makes it harder to reuse extracted artifacts across different retrieval backends.

Option B: extraction is embedded in corpus ingestion

- Ingest always runs extraction for certain media types.
- This violates the principle that raw items are the immutable source of truth.
- It makes it difficult to compare extraction implementations, because the corpus becomes tied to one extraction output.

Option C: extraction is a distinct plugin type and a distinct pipeline stage

- Extraction runs are built separately from retrieval runs.
- Extraction output is stored as derived artifacts under the corpus, partitioned by extraction plugin identifier and run identifier.
- Retrieval backends can build and query using a selected extraction run, without knowing which extraction implementation produced it.

Recommendation

Pick option C. It keeps the corpus raw and stable while allowing clean evaluation across extraction providers and across retrieval providers.

Outcome

This was implemented. Extraction is a distinct plugin stage with a command line interface entry point, and retrieval backends can reference a selected extraction run.

## Lifecycle hooks and where plugins can attach

The system already has a clear separation between raw items, the catalog, backend run builds, and retrieval queries. Lifecycle hooks make those boundaries explicit and give plugins a place to participate.

### Hook points to consider

Ingestion

- Before ingest: validate metadata and enforce corpus rules.
- After ingest: enrich metadata, add derived fields, and emit logs.

Catalog rebuild

- Before catalog rebuild: discover items and validate corpus structure.
- After catalog rebuild: compute corpus statistics and quality signals.

Backend run build

- Before backend build: choose input material, such as extracted text artifacts.
- After backend build: emit build metrics and record derived artifacts.

Query and evidence

- Before query: normalize the query and apply user preferences.
- After query: rerank, filter, and format evidence.

Evaluation

- Before evaluation: select dataset slices and enforce budgets.
- After evaluation: record metrics and regression signals.

### Decision 7: hook protocol design

Goal: allow plugins to attach to lifecycle points without turning the core into a plugin framework.

Option A: Python protocols with explicit hook interfaces

- Define a small set of Protocol or abstract base class types.
- Each hook point has a strongly typed context object modeled as a Pydantic type.
- The plugin returns an explicit result object modeled as a Pydantic type.
- Validation errors become clear command line interface errors instead of silent behavior.

Option B: a generic event bus with untyped dictionaries

- Flexible, but encourages drift in vocabulary and schema.
- Harder to validate and document.

Option C: treat every hook as a command line tool

- Plugins run as external processes.
- Strong isolation, but higher overhead and more moving parts.

Recommendation

Pick option A. This project values explicit vocabulary and validation. A typed hook interface with Pydantic models makes behavior precise and keeps plugins honest.

Outcome

Version zero implemented option A with a small hook protocol, hook configuration validation, and built in example hooks.

### Decision 8: how hook execution is recorded

Goal: a user should be able to answer what changed and why, especially when a plugin modifies metadata or produces derived artifacts.

Option A: a hook log file per run

- Each hook execution writes a record into a structured log.
- The log references item identifiers and explains changes.

Option B: write changes only into metadata

- Simple, but loses the history of why and when.

Option C: store a full audit trail database

- Powerful, but not aligned with the minimal file first corpus principle.

Recommendation

Pick option A. A structured log file is readable, portable, and sufficient for early auditing.

Outcome

Version zero implemented option A by writing structured log entries for hook execution.

## Outcomes and remaining questions

The hook protocol and hook logging policy above were implemented in version zero. This section records what was implemented, plus the questions that remain for future iterations.

### Hook contexts implemented in version zero

- Version zero defined a fixed set of hook points that covered ingest, catalog rebuild, backend build, query, and evaluation.
- Hook contexts were modeled as Pydantic types and passed into hooks as validated inputs.
- Multiple hooks were executed in a deterministic order based on configuration order.
- Hook failures were treated as hard errors and surfaced as clear command line interface errors.
- Hooks were treated as repeatable operations and were expected to be safe when a user reran a command.

### Hook log schema implemented in version zero

- Hook logs were written under `.biblicus/hook_logs/` as structured JavaScript Object Notation Lines files.
- Log entries included operation identifiers, timestamps, hook identifiers, hook points, and references to inputs and outputs.
- Sensitive information in source uniform resource identifiers was redacted.

### Remaining design questions

- Should hooks support asynchronous execution for long running transforms
- Should hooks support concurrency control when multiple operations run at the same time
- Should hook logs support a standard change patch format for metadata edits
- Should hook logs have an explicit retention policy beyond manual cleanup
- Should run artifacts and run manifests move to a partitioned layout by plugin type and identifier, as described above

## First behavior driven development slices implemented in version zero

These were small, concrete slices that were specified and built without committing to too much machinery.

- Import a folder tree into a corpus while preserving relative paths and provenance
- Corpus ignore file that prevents ingestion of known patterns
- Streaming ingestion that computes and records a checksum
- Content sniffing for a small set of file types to ensure useful file extensions
- A first lifecycle hook that runs after ingest and can add a tag or title

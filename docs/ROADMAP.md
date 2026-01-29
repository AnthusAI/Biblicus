# Roadmap

This document is the ordered plan for what to build next.

If you are looking for runnable examples, see `docs/DEMOS.md`.

## Principles

- Behavior specifications are the authoritative definition of behavior.
- Every behavior that exists is specified.
- Validation and documentation are part of the product.
- Raw corpus items remain readable, portable files.
- Derived artifacts are stored under the corpus and can coexist for multiple implementations.

## Current state

Version zero includes:

- A file based corpus with ingestion, catalog rebuild, import, ignore rules, and lifecycle hooks.
- A retrieval baseline (`scan`) and a practical local backend (`sqlite-full-text-search`).
- A separate text extraction stage with extraction runs and a composable extractor pipeline.
- Selection extractor steps that choose extracted text within a pipeline.
- A speech to text extractor plugin (`stt-openai`) implemented as an optional dependency.
- An optical character recognition extractor plugin (`ocr-rapidocr`) implemented as an optional dependency.
- A broad catchall extractor plugin (`unstructured`) implemented as an optional dependency.
- Integration corpora that include deterministic non-text cases such as a blank Portable Document Format file and a silence Waveform Audio File Format clip.

## Milestones

### Milestone 1: Portable Document Format text extraction plugin

Goal: extract usable text from Portable Document Format items without mutating raw corpus files.

Deliverables:

- A new extractor plugin that produces extracted text artifacts for Portable Document Format items.
- A dataset and evaluation approach that compares extractor outputs for accuracy, speed, and cost.

Acceptance checks:

- New behavior specifications describe the supported Portable Document Format subset.
- `python3 scripts/test.py` reports 100 percent coverage.
- `python3 scripts/test.py --integration` downloads sample Portable Document Format files and produces extracted text artifacts.

Status:

- The first extractor plugin exists as `pdf-text`.
- The evaluation dataset and metrics are still pending.

### Milestone 2: Optical character recognition plugin

Goal: extract usable text from image items as derived artifacts, with pluggable providers.

Deliverables:

- One local reference implementation, even if it is limited.
- A provider interface that can be backed by a local engine or a remote service.
- Evaluation metrics that report throughput and error rates.
- The optical character recognition plugin composes with selection extractor steps so you can compare it against other extractors.
- Additional speech to text plugins for audio items are planned as sibling milestones, using the same extraction pipeline and artifact layout.

Acceptance checks:

- A small corpus of test images can be downloaded by an integration script.
- Extraction runs record success, empty output, and skip counts per item.

Status:

- A reference extractor exists as `ocr-rapidocr`.
- Integration downloads include a deterministic blank image for stable empty-output cases.

### Milestone 3: Catchall extraction for wide format coverage

Goal: provide a last-resort extractor with broad file format support, while keeping it optional.

Deliverables:

- A catchall extractor plugin backed by the `unstructured` library.
- Integration coverage that validates Unstructured can extract usable text from at least one non-text format that other built-in extractors do not handle.
- Clear test gating so the base integration suite remains deterministic and does not require large optional dependencies.

Acceptance checks:

- `python3 scripts/test.py --integration` passes without installing Unstructured.
- `python3 scripts/test.py --integration --unstructured` passes when `biblicus[unstructured]` is installed.

Status:

- The extractor exists as `unstructured`.
- The mixed integration corpus includes a `.docx` sample that Unstructured can extract.

### Milestone 4: Selection policies for competing extractors (next)

Goal: make extractor choice explicit, reproducible, and testable when multiple extractors can produce text for the same item.

Deliverables:

- A selection extractor that can choose among prior pipeline outputs using an explicit policy.
- Provenance that records which step produced the chosen output and why it was chosen.

Acceptance checks:

- Behavior specifications cover selection policy behavior and tie-breaking.
- The selection policy is implemented as an extractor step so it is versioned as part of the extraction run.

Status:

- A minimal selection step exists as `select-text` (first usable output).
- A deterministic content-based selection step exists as `select-longest-text` (longest usable output).
- A quality-aware selection step remains a next milestone.

### Milestone 5: Scanned Portable Document Format extraction (next)

Goal: extract usable text from scanned Portable Document Format files using optical character recognition, without mutating raw files.

Deliverables:

- A scanned Portable Document Format sample that contains no extractable text via `pdf-text`.
- An optical character recognition based pipeline that produces usable text from that same file.
- A comparison story that makes it easy to evaluate `pdf-text`, optical character recognition, and Unstructured against the same raw item.

Acceptance checks:

- Integration coverage includes a scanned Portable Document Format case and verifies expected differences across extractors.
- The pipeline remains composable: optical character recognition is independent from retrieval backends and independent from Unstructured.

### Milestone 6: Evidence quality stages

Goal: add explicit rerank and filter stages to retrieval.

Deliverables:

- A rerank stage interface that takes evidence and returns reordered evidence.
- A filter stage interface that applies metadata and source constraints.
- Documentation that explains how to configure budgets and stage ordering.

Acceptance checks:

- Behavior specs cover the new stages.
- Evaluation reports show per stage metrics and final metrics.

### Milestone 7: Evaluation reports and datasets

Goal: make evaluation results easier to interpret and compare.

Deliverables:

- A dataset authoring workflow that supports small hand labeled sets and larger synthetic sets.
- A report that includes per query diagnostics and a clear summary.

Acceptance checks:

- The existing dataset format remains stable or is versioned.
- Reports remain deterministic for the same inputs.

### Milestone 8: Pluggable backend hosting modes

Goal: add one reference backend in an external process or remote service mode.

Deliverables:

- A tool server that exposes a backend through a stable interface.
- Documentation that shows how to run a backend out of process and connect to it.

Acceptance checks:

- Local tests remain fast and deterministic.
- Integration tests validate end to end retrieval through the tool boundary.

## Where to put design notes

Design notes live in `docs/` so they are easy to browse and cross link.

Executable behavior lives in `features/*.feature`.

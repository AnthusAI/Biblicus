# Biblicus (Project Memory)

## What we're building

- **Biblicus**: a product and reference implementation for **managing knowledge bases** (ingest, curate, query) and **evaluating** different retrieval and retrieval-augmented generation approaches against shared data, including a **pluggable interface** for connecting knowledge base backends to **Tactus procedures**.

Tactus is a separate project: an imperative, sandboxed Lua domain-specific language and runtime for durable agent workflows. Tactus intentionally does *not* include a knowledge base user interface or opinionated knowledge base management.

## Core goals

- Make knowledge bases **pluggable** for Tactus procedures.
- Keep a **single source of truth** for raw content while supporting **multiple derived representations** (chunks, embeddings, indexes) across different backends.
- Support **experimentation and evaluation**: compare knowledge base implementations and retrieval and retrieval-augmented generation patterns with consistent datasets and metrics.
- Provide a usable baseline: ingest documents and query them interactively (even before advanced retrieval-augmented generation research features).

## Early minimum viable product (near-term)

- Command-line interface first: a `biblicus` command with subcommands focused on **raw ingestion** and **basic inspection**.
- Default "data lake" should impose minimal opinions: support **a plain folder of unstructured files** as an ingestion source and/or workspace.
- Optional convenience: support **Markdown + Yet Another Markup Language front matter** as a human-friendly way to add tags and metadata.
- Corpora are identified by a uniform resource identifier (paths normalize to `file://...`); the derived index is rebuildable via re-indexing.
- Metadata can live in Markdown front matter or adjacent sidecars (for example, `file.pdf.biblicus.yml`).
- The core ingestion primitive is **item-centered**: an **Item** is raw bytes of any modality + optional metadata + provenance.

## Locked decisions (version zero)

- **Evidence is the primary output**: retrieval returns structured evidence with identifiers, provenance, and scores; any “context pack” is derived.
- **Multi-stage retrieval** is explicit (retrieve, rerank, then filter) and expressed via evidence metadata.
- **Context budgeting** governs evidence selection (token, unit, and per-source limits), not a fixed count.
- **Deterministic lexical baseline, hybrid target**: deterministic lexical backend first; hybrid retrieval is the strategic direction.
- **Evaluation datasets are mixed**: human-labeled for truth, synthetic for scale.
- **Corpus snapshots are versioned**: reindex and snapshot builds get identifiers for reproducibility.
- **Extraction cache identity is name-based**: changing the extraction configuration name produces a new snapshot identity and invalidates cached artifacts.

## Agent orientation

- **Primary objective**: Biblicus manages raw corpora and evaluates retrieval and retrieval-augmented generation backends used by Tactus.
- **Canonical vocabulary**: `corpus`, `item`, `catalog` (internal-only), `configuration`, `evidence`, `snapshot`, `snapshot artifacts`, `pipeline stage`.
- **Non‑negotiables**: evidence is the primary output; multi‑stage retrieval; context budgets; deterministic lexical baseline and hybrid target; mixed evaluation datasets; versioned snapshots.
- **Behavior-driven development discipline**: specifications first; every behavior specified; one official way (no fallbacks).
- **Modeling discipline**: Pydantic at boundaries; validation errors must be clear.
- **Development flow**: update `features/*.feature`, implement, run tests; use the command-line interface to ingest; `reindex` refreshes catalog.

## Strict behavior-driven development policy (project-wide)

- **Specifications first**: new behavior starts in `features/*.feature` and should fail before implementation begins.
- **Single vocabulary**: scenarios must use the domain-specific cognitive framework terms (avoid synonyms that drift over time).
- **No "just tests"**: behavior specifications are part of the architecture; they define what the system *is*.
- **Specification completeness**: every behavior that exists must be specified. If a behavior cannot be specified clearly, it should not exist (remove it or make it a hard error).
- **100% test coverage is required**: all code must be covered by BDD tests. This is non-negotiable.

## CRITICAL: No Backward Compatibility or Fallback Logic (project-wide)

**This is a strict, non-negotiable policy across the entire Biblicus project:**

- **NO backward compatibility code**: Never preserve old code paths when updating to a new approach
- **NO fallback logic**: Never check multiple locations or try alternative approaches
- **NO "support both ways"**: There is ONE correct way, implement that way only
- **NO legacy support**: Old structures are upgraded through migration, not supported forever
- **ONE way to do things**: If there's a new metadata location, use ONLY that location

**Why this matters:**
- Fallback logic creates exponential complexity
- Multiple code paths mean multiple failure modes
- Backward compatibility prevents evolution
- "Just in case" code becomes permanent debt

**What to do instead:**
- Implement the current, correct approach cleanly
- If old data exists, fail gracefully and show what you can
- Progressive enhancement: display available data, skip missing data
- Clear error messages when data is missing
- Document migration paths separately (don't mix with runtime code)

**Examples of what NOT to do:**
```python
# WRONG - trying both locations with fallback
try:
    data = read_from_new_location()
except:
    try:
        data = read_from_old_location()  # NO! Don't do this!
    except:
        data = None
```

**Examples of what TO do:**
```python
# RIGHT - one location, fail gracefully
try:
    data = read_from_metadata_folder()
    display_full_info(data)
except FileNotFoundError:
    # Gracefully show what we can without that data
    display_basic_info()
```

## Working backwards (product-first workflow)

- **Start with a PR-FAQ draft** for every new feature. The AI coding agent writes it as a draft to demonstrate product understanding.
- **Review the PR-FAQ first**, then decide whether the feature should proceed.
- **Only after PR-FAQ approval**, write the README and Sphinx docs as if the feature already exists.
- **Then write BDD specs** in `features/*.feature` that reflect the documentation.
- **Only then implement the feature**, following the documentation and specs exactly.
- **Finish by enforcing quality gates**: docstrings, validation, naming clarity, and 100% coverage.

## Documentation as a runnable textbook

- **Documentation is as important as code**: Sphinx pages are treated as a textbook that teaches the concepts and the Biblicus implementation.
- **Elementary, educational examples**: prefer basic, textbook methods first, then build up to advanced techniques.
- **Runnable narratives**: every concept described in the docs must have a working example users can run on bundled demo data.
- **Learning by doing**: demos should be executable end to end and reusable on user-provided data.
- **Teach by example**: explanations should connect to actual Biblicus commands, scripts, and outputs.

## One official way (no compatibility baggage)

- No backwards compatibility layers, no legacy aliases, no “support both”.
- No hidden fallbacks that hide mistakes; prefer explicit errors and clear guidance.
- The domain-specific cognitive framework vocabulary is authoritative: we pick one set of nouns and use them everywhere (code, command-line interface, documentation, specifications).

## Pydantic-first domain modeling

- Domain constructs should be represented as **Pydantic models** whenever they cross a boundary (configurations, application programming interfaces, tool schemas, command-line interface output).
- Validation errors should be converted into clear, user-facing messages (especially in command-line interface and tool contexts).

## Semantic versioning and releases

- **Semantic release is fully automated in GitHub Actions**: version bumps, changelog generation, and PyPI publishing are handled by the `python-semantic-release` workflow.
- **Do NOT manually update version numbers** (e.g., in `pyproject.toml` or `src/biblicus/__init__.py`).
- **Do NOT manually edit the CHANGELOG.md file**.
- **Use conventional commits** for all commits: prefix with `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, etc. to trigger the appropriate semantic version bump.
- The workflow parses commit messages to determine the next version (major, minor, patch) and automatically generates release notes.
- Local development should focus on writing code and tests; versioning and publishing are automated on `main` after code review.

## Coding style policies

- **No line-level comments**. Comments create drift and obscure clarity. Prefer long, descriptive names and small, readable functions.
- **Block comments only** when capturing a high-level idea or rationale; no step-by-step narration.
- **Sphinx-style docstrings** are required for public functions, classes, and modules, using reStructuredText field lists (`:param`, `:type`, `:return`, `:rtype`, `:raises`, `:ivar`, `:vartype`).
- **Black + Ruff compliance** is mandatory.
- **Documentation tooling** must be included for docstring generation.
- **Intent over code**: invest more tokens in specifications, docstrings, validation, and types than in implementation. The documentation is part of the product.

### Comment policy examples

Bad:
```python
def ingest(data, path):
    # write bytes to disk
    with open(path, "wb") as handle:
        handle.write(data)
```

Good:
```python
from pydantic import BaseModel, Field


class RawItemWriteRequest(BaseModel):
    """
    Request to persist raw item bytes to disk.

    :param raw_item_bytes: Raw item payload to persist.
    :type raw_item_bytes: bytes
    :param destination_path: File system path for the persisted bytes.
    :type destination_path: str
    """

    raw_item_bytes: bytes = Field(min_length=1)
    destination_path: str = Field(min_length=1)


def persist_raw_item_bytes(request: RawItemWriteRequest) -> None:
    """
    Persist raw item bytes to the destination path.

    :param request: Validated request containing the raw item bytes and destination path.
    :type request: RawItemWriteRequest
    :return: None. This function writes bytes to disk and returns no value.
    :rtype: None
    :raises OSError: If the destination path cannot be written.
    """
    with open(request.destination_path, "wb") as destination_handle:
        destination_handle.write(request.raw_item_bytes)
```

## Non-goals (early)

- Rebuilding vector databases or general search engines.
- Forcing a single "best" retrieval-augmented generation pattern.
- Putting a full knowledge base user interface inside Tactus itself.

## Constraints learned from Tactus

- Tactus integrates capabilities via **tools and toolsets** (including external tools via the **Model Context Protocol** with `Tool.get()`), and via declared **dependencies** (hypertext transfer protocol, database, cache) injected into tools.
- Tactus emphasizes **least-privilege**, **sandboxing**, and **secretless or brokered execution** (sensitive tools can run outside the sandbox).
- Tactus treats **durability and checkpointing** and **evaluations** as primary concerns; Biblicus's knowledge base interface should align with these (idempotent operations, observable metrics).

## Aesthetic principles (Tactus-adjacent)

- Keep the **core language small and orthogonal**; prefer composing primitives over adding domain-specific ones.
- Seek **clear ergonomics** via libraries and wrappers first; only add language primitives when they unlock semantics you cannot express cleanly with tools (for example, enforceable policy boundaries, runtime-managed durability and caching, or guaranteed instrumentation).

## Assistant role (working style)

- Act as an **opinionated expert advisor**: I will push back on ideas that increase complexity, reduce reproducibility, or conflict with Tactus's model.
- Provide **multiple viable options** with clear tradeoffs, then give a recommendation and say why.
- Prefer **minimal-opinion minimum viable products**, but insist on the *smallest set of invariants* needed for reliable evaluation (identifiers, provenance, versioning).
- Keep this file updated as the project evolves (names, scope boundaries, key abstractions, and architectural choices).

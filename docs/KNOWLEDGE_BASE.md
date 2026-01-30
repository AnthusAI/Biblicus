# Knowledge base

The knowledge base is the high‑level, turnkey workflow that makes Biblicus feel effortless. You hand it a folder. It chooses sensible defaults, builds a retrieval run, and gives you evidence you can turn into context.

This is the right layer when you want to use Biblicus without spending time on setup. You can still override the defaults later when you want fine‑grained control.

## What it does

- Creates or opens a corpus at a chosen location (or a temporary location if you do not provide one).
- Imports a folder tree into that corpus.
- Builds a retrieval run using a default backend.
- Exposes a simple `query` method that returns evidence.
- Exposes a `context_pack` helper to shape evidence into model context.

## Minimal use

```python
from biblicus.knowledge_base import KnowledgeBase


kb = KnowledgeBase.from_folder("notes")
result = kb.query("Primary button style preference")
context_pack = kb.context_pack(result, max_tokens=800)

print(context_pack.text)
```

## Default behavior

The knowledge base wraps existing primitives. Defaults are explicit and deterministic.

- **Corpus**: stored on disk and fully inspectable.
- **Import**: uses the folder tree import, preserving relative paths.
- **Backend**: defaults to the `scan` backend.
- **Query budget**: defaults to a small, conservative evidence budget.

## Output structure

`KnowledgeBase.query` returns a `RetrievalResult` with evidence you can inspect or pass into context pack shaping.
`KnowledgeBase.context_pack` returns a structured context pack with per-block metadata.

These are the same structures produced by the lower-level retrieval and context pack APIs, so you can reuse existing
evaluation and inspection tools.

## Overrides

You can override the defaults when needed.

```python
from biblicus.knowledge_base import KnowledgeBase
from biblicus.models import QueryBudget


kb = KnowledgeBase.from_folder(
    "notes",
    backend_id="scan",
    recipe_name="Knowledge base demo",
    query_budget=QueryBudget(max_total_items=10, max_total_characters=4000, max_items_per_source=None),
    tags=["memory"],
    corpus_root="corpora/knowledge-base",
)
```

## How it relates to lower‑level control

The knowledge base is a convenience layer. It uses the same underlying parts that the lower‑level examples use.

- `Corpus` for ingestion and storage
- `import_tree` for folder ingestion
- A backend run (`scan` by default)
- `QueryBudget` for evidence limits
- `ContextPackPolicy` and token fitting for context shaping

You can always drop down to those lower‑level primitives when you need more control.

If the high‑level workflow is not enough, switch to `Corpus`, `get_backend`, and `ContextPackPolicy` directly.

## Reproducibility checklist

- Record the corpus path and catalog timestamp.
- Capture the backend run identifier used by the knowledge base.
- Persist the query budget used for comparisons.

## Common pitfalls

- Comparing results from knowledge bases built on different corpus roots.
- Forgetting to capture the run identifier before rebuilding the corpus.

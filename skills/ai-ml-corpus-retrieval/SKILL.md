---
name: ai-ml-corpus-retrieval
description: Use when an agent needs to get information out of the Biblicus AI-ML-Research corpus quickly through supported Biblicus commands, including topic context reports, evidence search, research-intake triage, pending-review lists, topic trends, or graph extraction status. Use this instead of manually reading raw corpus files or sidecars when answering questions, preparing research-agent context, screening new candidates, or producing evidence-backed corpus summaries.
---

# AI-ML Corpus Retrieval

## Core Rule

Use Biblicus commands as the access layer. Do not start by reading individual corpus files, PDFs, HTML payloads, or sidecars. Use raw file inspection only when the user explicitly asks for a specific stored artifact or when a Biblicus command returns an item ID that must be inspected with `biblicus show`.

Run commands from `/Users/ryan/Projects/Biblicus` with `.venv/bin/python -m biblicus`. The corpus is `corpora/AI-ML-research`.

## Decision Flow

1. Need a compact map of what the knowledge base contains:
   Use `.venv/bin/python -m biblicus analyze topic-context`.

2. Need to search for evidence matching a phrase:
   Use `.venv/bin/python -m biblicus query` against a retrieval snapshot. If no snapshot exists, build one through `.venv/bin/python -m biblicus build`.

3. Need to decide whether a new local item belongs in the corpus:
   Create a metadata file, retrieve the item to a local file outside Biblicus, then use `.venv/bin/python -m biblicus research-intake assess` first. Use `research-intake ingest` only after assessment.

4. Need human-review work:
   Use `.venv/bin/python -m biblicus research-intake pending`.

5. Need temporal/trending topic signals:
   Use `.venv/bin/python -m biblicus analyze topic-trends` against a topic-modeling snapshot.

6. Need application/steering import data or artifact discovery:
   Use `.venv/bin/python -m biblicus steering export` or `.venv/bin/python -m biblicus steering artifacts`.

7. Need GraphRAG artifacts:
   Use `.venv/bin/python -m biblicus graph list`, `graph show`, or `graph extract`. Treat graph extraction as an artifact stage; do not assume a graph-aware retriever exists unless the repo has one.

## Required Outputs

For user-facing answers, report evidence in Biblicus terms:

- `item_id`
- title
- source URI
- topic label or topic ID when relevant
- retrieval score or classifier score when available
- snapshot or model identifier when the result depends on one

When a command emits JSON, summarize the useful fields instead of pasting the full payload unless the user asks for raw JSON.

## Command Recipes

For exact command patterns and interpretation notes, read [references/biblicus-ai-ml-commands.md](references/biblicus-ai-ml-commands.md).

---
name: research-workflow
description: Use when an agent is doing corpus expansion work: find candidate research papers or articles, retrieve the raw artifact outside Biblicus, write canonical Biblicus metadata (including dates.published_at), run research-intake assess/ingest, and manage the pending_review queue with research-intake decide (accept, tag, or delete on reject).
---

# Research Workflow (Biblicus)

## Core Rules

1. Biblicus does not download or enrich sources. Retrieve artifacts outside Biblicus, then ingest local files.
2. Every candidate must have a metadata file with at least `title`, `abstract`, `dates.published_at`, and `tags: [ai-ml-research]`.
3. Always use the intake gate:
   - assess: `biblicus research-intake assess`
   - ingest: `biblicus research-intake ingest`
4. Rejections are deleted (raw file + sidecar) to keep the corpus clean.

## Step 0: Kanbus Task (Mandatory)

Before doing a research/ingest sweep, create or update a Kanbus task for it. Do not read or write `project/` directly.

## Step 1: Find Candidates (Discovery)

Use sources that provide stable identifiers and canonical PDFs:

- arXiv (preferred for papers): search by keywords and follow `arxiv.org/abs/<id>`.
- Hugging Face Papers: useful for surfacing trending arXiv papers and getting quick dates.
- Papers with Code: useful for task-centric discovery and related-paper graphs.
- Hacker News: useful for “paper becomes product” or widely discussed systems papers.

Discovery output should be a shortlist of `source_uri` values (one per candidate) plus the canonical identifier (arXiv id or DOI) when available.

## Step 2: Retrieve the Artifact (Outside Biblicus)

Preferred artifacts:

- For arXiv: download the canonical PDF from `https://arxiv.org/pdf/<id>.pdf` and set `--source-uri` to `https://arxiv.org/abs/<id>`.
- For web articles: save an offline copy (PDF or HTML) that is stable enough for future re-indexing.

Keep a local intake folder (example):

```bash
mkdir -p /tmp/biblicus-intake/<topic>
```

## Step 3: Write Canonical Metadata (YAML)

Canonical shape (minimum required fields included):

```yaml
title: "..."
abstract: "..."
authors:
  - "..."
dates:
  published_at: "YYYY-MM-DD"
  updated_at: "YYYY-MM-DD"         # optional
  retrieved_at: "YYYY-MM-DDThh:mm:ssZ"  # optional
date_provenance:
  published_at: "source-metadata"  # or "curator"
  updated_at: "source-metadata"    # optional
tags:
  - ai-ml-research
curation:
  proposed_topic_uid: "..."
```

Date rules:

- Prefer `YYYY-MM-DD` unless the source provides time precision.
- Trend analysis should use `dates.published_at` (not `created_at`, `retrieved_at`, or legacy fields).

## Step 4: Assess (Do Not Ingest Yet)

```bash
uv run biblicus research-intake assess \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./item.biblicus-input.yml \
  ./item.pdf
```

Interpretation:

- `accepted`: ingest it.
- `pending_review`: ingest it, but it stays out of topic modeling until reviewed.
- `rejected`: do not ingest.

## Step 5: Ingest (Only Through Intake Gate)

```bash
uv run biblicus research-intake ingest \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./item.biblicus-input.yml \
  --source-uri "https://example.org/source" \
  ./item.pdf
```

Notes:

- Use the best canonical `--source-uri` you have (arXiv abs URL, DOI landing page, publisher page).
- Ingest enforces de-duplication; if the same paper arrives via multiple URLs, ingestion should refuse collisions rather than silently duplicating content.

## Step 6: Pending-Review Triage (Accept/Reject + Tagging)

List pending:

```bash
uv run biblicus research-intake pending \
  --corpus corpora/AI-ML-research \
  --format markdown
```

Accept (and add tags / optionally set a reviewed topic):

```bash
uv run biblicus research-intake decide \
  --corpus corpora/AI-ML-research \
  --item-id <uuid> \
  --decision accept \
  --tags-add process-mining \
  --tags-add workflow-automation
```

Reject and delete (preferred):

```bash
uv run biblicus research-intake decide \
  --corpus corpora/AI-ML-research \
  --item-id <uuid> \
  --decision reject \
  --delete
```

## Step 7: Handoff (What “Done” Looks Like)

For a sweep, the expected handoff is:

- Items ingested (accepted or pending_review).
- Rejected candidates not ingested (or deleted if already ingested as pending).
- Current pending queue output:

```bash
uv run biblicus research-intake pending --corpus corpora/AI-ML-research --format markdown
```

And for each notable item, at least: `item_id`, title, `dates.published_at`, and `source_uri`.

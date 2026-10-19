# Research Agent Intake

Research agent intake is the gate between outside research and a Biblicus corpus. It is for already-retrieved local
items: the agent supplies a file plus curated metadata, and Biblicus decides whether the item should enter the corpus as
eligible, enter as pending review, or not enter at all.

## Candidate metadata

The first version assesses metadata text only. The metadata file must be a YAML or JSON object with `title` and
`abstract`. For non-paper web articles, write an abstract-like summary in `abstract`.

```yaml
title: "Self-Evolving Scientific Agents"
abstract: "A concise description of the candidate item and why it may belong in this corpus."
dates:
  published_at: "2026-05-15"
tags:
  - ai-ml-research
```

Research agents should keep the assessment text neutral. Do not put the expected decision, desired topic label, or
human-facing request in `abstract`. Candidate hints belong in tags or curation metadata, and accepted canonical topics
still require human-reviewed manifests.

## Research agent operating contract

Research agents use the gate in two phases:

1. Run `assess` while screening candidates. This returns the intake decision and writes nothing.
2. Run `ingest` only for candidates that should be stored when the decision is `accepted` or `pending_review`.

The decisions mean:

- `accepted`: eligible for the corpus and future topic workflows, but not a topic seed.
- `pending_review`: stored for human review and excluded from topic modeling, classifier training, trend reports, and
  topic context until accepted.
- `rejected`: not stored by the intake command.

The default AI-ML configuration accepts when a mapped classifier topic has score at least `0.60` and corpus similarity
is at least `0.08`. It rejects only when corpus similarity is below `0.08` and the classifier is missing, unmapped, or
below `0.20`. Everything else becomes `pending_review`.

## Assess without storing

```bash
biblicus research-intake assess \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  ./paper.pdf
```

The command returns JSON with the decision, classifier prediction, corpus similarity, nearest evidence item identifiers,
and the metadata Biblicus would write if the item were ingested. It does not modify the corpus.

## Ingest through the gate

```bash
biblicus research-intake ingest \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  --source-uri https://example.org/paper \
  ./paper.pdf
```

Accepted and pending items are stored with the standard single-item ingest behavior. Rejected items are not stored.
Accepted items receive `curation.intake_status: accepted`; pending items receive `curation.intake_status:
pending_review`.

## Review queue

```bash
biblicus research-intake pending \
  --corpus corpora/AI-ML-research \
  --format markdown
```

Approve or reject a pending item:

```bash
biblicus research-intake decide \
  --corpus corpora/AI-ML-research \
  --item-id <item-id> \
  --decision accept \
  --topic-uid automated-scientific-discovery
```

Accepted items become eligible for topic modeling after reindexing. Rejected items remain in the corpus as an audit
record but stay excluded from topic modeling.

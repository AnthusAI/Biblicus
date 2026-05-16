# AI-ML-Research Corpus Agent Notes

This corpus stores AI/ML research papers as raw local files plus Biblicus sidecar metadata. Do not move papers into topic folders to create labels. Use metadata and future classifier manifests for topic experiments.

## Add One New Item

Biblicus does not retrieve papers for this workflow. First download or otherwise obtain the paper locally, then create a curated metadata YAML or JSON file next to your working copy.

Example metadata file:

```yaml
title: "Example Research Paper"
authors:
  - "Example Author"
abstract: "Research abstract from the source, or a neutral curator-written summary when the source has no abstract."
dates:
  published_at: "2026-05-15"
date_provenance:
  published_at: "source-metadata"
tags:
  - ai-ml-research
  - candidate-topic-tag
curation:
  intent: topic-seed-candidate
  proposed_topic_uid: candidate-topic
  note: "Candidate paper for human review; not seed material until explicitly promoted."
```

Ingest the already-retrieved local file with the standard single-item command:

```bash
biblicus ingest --corpus corpora/AI-ML-research ./paper.pdf \
  --metadata-file ./paper.biblicus-input.yml \
  --source-uri https://example.org/paper-or-landing-page \
  --published-at 2026-05-15 \
  --tag ai-ml-research
```

Use `--media-type application/pdf` only when filename sniffing is insufficient.
Use `dates.published_at` for trend analysis. Do not add top-level `published` metadata.

## Verify The Item

After ingest, verify that the sidecar and catalog entry exist:

```bash
biblicus reindex --corpus corpora/AI-ML-research
biblicus show --corpus corpora/AI-ML-research <item-id>
```

The sidecar should be named like `<stored-file>.biblicus.yml` and should include `biblicus.id`, `biblicus.source`, the stored media type, tags, and the curated metadata fields from the metadata file.

## Research-Agent Intake Triage

Use the intake gate for research-agent corpus expansion. Do not use plain `biblicus ingest` for newly researched
AI/ML candidates unless a human explicitly tells you to bypass triage. Retrieval happens outside Biblicus: download the
file or save the web article locally first, then create one metadata YAML or JSON file.

The metadata file must include:

```yaml
title: "Candidate title"
abstract: "Research-paper abstract, or a curator-written abstract-like summary for a web article."
dates:
  published_at: "2026-05-15"
tags:
  - ai-ml-research
```

For web articles, `abstract` is still the required assessment text. Write a concise neutral summary that explains the
technical subject of the item. Do not include your intake decision in the `abstract`; candidate labels belong under
`tags` or `curation.proposed_topic_uid`.

### 1. Assess First When Screening Candidates

Use `assess` to classify a candidate without changing the corpus:

```bash
biblicus research-intake assess \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  ./paper.pdf
```

Interpret the JSON decision this way:

- `accepted`: The item matches an existing topic strongly enough and is similar enough to the corpus. Ingest it through
  `research-intake ingest`. It becomes a normal eligible corpus item, but it is not automatically a seed.
- `pending_review`: The item may be relevant, but it may be weakly matched, borderline, or potentially a new category.
  Ingest it through `research-intake ingest` so humans can review it later. Pending items stay in this corpus but are
  excluded from topic modeling, classifier training, trend reports, and topic context until accepted.
- `rejected`: The item is not relevant enough for this corpus. Do not ingest it. Include the title and source URI in
  your handoff as rejected candidate evidence.

### 2. Ingest Only Through The Gate

When the candidate should be stored if accepted or pending, run:

```bash
biblicus research-intake ingest \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  --source-uri https://example.org/paper-or-landing-page \
  ./paper.pdf
```

The command runs the same assessment. If the decision is `rejected`, it writes nothing. If the decision is `accepted` or
`pending_review`, it stores the raw item, writes the sidecar, reindexes the corpus, and records the intake assessment
under `curation.intake_assessment`.

Use `--media-type` only when filename sniffing is wrong. Use `--tag` only for stable corpus tags or candidate batch
tags; do not use tags as accepted topic labels.

### 3. Surface Human Review Work

Review pending items with:

```bash
biblicus research-intake pending \
  --corpus corpora/AI-ML-research \
  --format markdown
```

Include the pending list in the research-agent handoff when any item is pending. Humans can later decide an item:

```bash
biblicus research-intake decide \
  --corpus corpora/AI-ML-research \
  --item-id <item-id> \
  --decision accept \
  --topic-uid <topic-uid>
```

Only humans or explicitly delegated curator agents should run `decide`. `--decision accept` makes the item eligible for
topic workflows after reindexing. `--decision reject --delete` removes rejected pending-review raw files and sidecars.

## Relationship To AI-ML-History

This corpus is the authority for research-paper topics. Article-format AI/ML history material belongs in
`corpora/AI-ML-history`, not here. Do not add or reintroduce a `machine-learning-history` topic in the
`ai-ml-research` seed manifest. Historically important research papers still stay here when they are in paper format.

The history corpus is projection-only. Train topic classifiers from this research corpus, then project predictions onto
history articles with provenance recorded in the history corpus.

## Authority Classifier Maintenance

For mixed PDF and HTML topic modeling, use the corpus topic-text extraction recipe before discovery or classifier training:

```bash
biblicus extract build \
  --corpus corpora/AI-ML-research \
  --configuration configurations/extraction/ai-ml-research-topic-text.yml \
  --configuration-name ai-ml-research-topic-text \
  --force
```

Do not use raw `text/html` pass-through snapshots for topic modeling, because page markup can dominate topic keywords.

Train the canonical authority classifier from the research corpus only:

```bash
biblicus topic-classifier train \
  --corpus corpora/AI-ML-research \
  --manifest corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json \
  --configuration configurations/topic-classifier.yml \
  --configuration-name ai-ml-research \
  --extraction-snapshot pipeline:<research_snapshot_id>
```

The classifier id is `ai-ml-research`. Do not create manually numbered classifier ids; retraining creates automatic
model-version hashes under `analysis/topic-classifier/<model_version>/`.

After training, project the authority classifier onto AI/ML history articles:

```bash
biblicus topic-classifier project \
  --classifier-corpus corpora/AI-ML-research \
  --target-corpus corpora/AI-ML-history \
  --classifier ai-ml-research \
  --extraction-snapshot pipeline:<history_snapshot_id> \
  --all \
  --top-k 5 \
  --record \
  --format markdown
```

Projection records belong under
`corpora/AI-ML-history/metadata/topic-classifiers/ai-ml-research/predictions.jsonl`. Do not write projection records in
the research corpus for history articles.

## Review New Topic Candidates

Research agents may add blind candidate batches with tags like `automated-scientific-discovery-candidate` and metadata
`curation.proposed_topic_uid`. Do not promote these candidates into seeds during ingest.

After a batch is ingested, rebuild extraction and run unsupervised discovery. Then produce a review table with:

```bash
biblicus topic-classifier review-batch \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --extraction-snapshot pipeline:<snapshot_id> \
  --topic-modeling-snapshot <topic_modeling_snapshot_id> \
  --candidate-tag automated-scientific-discovery-candidate \
  --proposed-topic-uid automated-scientific-discovery \
  --format markdown
```

The review table is evidence for a human decision. It is not training data. Use `--record` only when an audit log of the
blind predictions is wanted.

Keep classifier names simple. Routine learning should rely on reviewed manifest files plus automatic model-version
hashes from training rather than manual name increments. If a candidate topic is accepted, draft a new manifest file and
train it; do not edit the canonical baseline file casually during blind intake review.

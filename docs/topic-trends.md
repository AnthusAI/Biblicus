# Topic trends

Topic trends combine exploratory topic modeling with corpus publication dates. They answer a different question from the topic classifier:

- topic classifiers describe stable, reviewed knowledge-base categories;
- topic trends describe time-sensitive publication momentum inside discovered clusters.

## Date metadata

Trend analysis uses one canonical field:

```yaml
dates:
  published_at: "2025-08-01"
```

Optional related fields can be stored beside it:

```yaml
dates:
  published_at: "2025-08-01"
  updated_at: "2025-08-14"
  retrieved_at: "2026-05-15T20:30:00Z"
date_provenance:
  published_at: source-metadata
```

Do not use ingest `created_at`, retrieval time, or legacy top-level `published` metadata for trends.

## Run a trend report

Run topic modeling first, then analyze trends from that snapshot:

```bash
biblicus analyze topic-trends \
  --corpus corpora/AI-ML-research \
  --topic-modeling-snapshot <snapshot_id> \
  --classifier ai-ml-research \
  --windows 30d,90d,1y,all \
  --format markdown
```

The report writes immutable artifacts under:

```text
analysis/topic-governance/<snapshot_id>/
```

The directory contains:

- `manifest.json`: reproducibility inputs for the report;
- `output.json`: ranked canonical and discovered topic summaries;
- `proposals.json`: unified steering proposal records;
- `report.md`: Markdown rendering of the report.

Markdown tables show the human-readable topic label beside the BERTopic topic identifier. When the topic modeling
snapshot used a BERTopic representation model, the label is the representation-model label rather than only the first
keyword fragment.

## Momentum ranking

Momentum compares a topic's recent publication-window share to its all-time share in the trend-eligible corpus. The default ranking window is `90d`.

Undated items are not included in these counts. The report lists them in warnings so curators can decide whether metadata cleanup is needed.

## Propose-only governance

Governance proposals use the unified steering proposal contract. They can recommend new topics, relabeling, merging, splitting, or archiving. The first implementation emits `new-topic` recommendations for discovered clusters with enough evidence. A proposal payload includes a topic identity, label, description, evidence item identifiers, suggested seeds, and suggested holdouts. When a discovered topic has a BERTopic representation-model label, that label becomes the proposed display name.

The proposal does not change the accepted classifier manifest. If a curator accepts it, they draft a new reviewed manifest and train a new model version.

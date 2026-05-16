# Biblicus AI-ML Command Recipes

Use these recipes from `/Users/ryan/Projects/Biblicus`.

## Candidate Metadata File

The intake metadata file is a strict YAML or JSON object. For research-agent intake, `title` and `abstract` are required. For non-paper web articles, write a neutral abstract-like summary in `abstract`.

Recommended arXiv paper shape:

```yaml
title: "NewtonBench: Benchmarking Generalizable Scientific Law Discovery in LLM Agents"
abstract: "NewtonBench evaluates language-model agents on interactive scientific law discovery tasks, using counterfactual physics-law shifts to test exploration, robustness, and generalization beyond memorized formulas."
authors:
  - "Tianshi Zheng"
  - "Kelvin Kiu-Wai Tam"
arxiv_id: "2510.07172"
pdf_url: "https://arxiv.org/pdf/2510.07172"
source_platform: "arXiv"
source_type: "research_paper"
dates:
  published_at: "2025-10-08"
  updated_at: "2026-02-24"
date_provenance:
  published_at: "source-metadata"
  updated_at: "source-metadata"
tags:
  - ai-ml-research
  - paper
  - arxiv
  - corpus-expansion-candidate
  - automated-scientific-discovery-candidate
curation:
  proposed_topic_uid: automated-scientific-discovery
  intent: topic-candidate
  source_selection: "Canonical arXiv PDF selected over discovery wrappers or discussion pages."
```

Rules:

- Use `dates.published_at` in `YYYY-MM-DD` form when a publication date is available.
- Use `dates.updated_at` only when source metadata exposes a meaningful revision/update date.
- Keep `abstract` neutral. Do not write the desired intake decision or ask the human for approval inside the abstract.
- Use `curation.proposed_topic_uid` for candidate-topic hints. Do not use tags as accepted topic labels.
- Include `ai-ml-research` on every item in this corpus.

## Tag Vocabulary

Use tags conservatively. These are working conventions, not accepted taxonomy definitions:

- `ai-ml-research`: required corpus tag.
- `paper`: research paper or preprint.
- `article`: web article, blog post, magazine article, or non-paper source.
- `arxiv`: item came from arXiv.
- `corpus-expansion-candidate`: item was found during research expansion.
- `<topic-uid>-candidate`: blind candidate for a proposed topic, such as `automated-scientific-discovery-candidate`.

Prefer `curation.proposed_topic_uid: <topic-uid>` for the candidate topic identity. Tags are search and batch-review hints.

## From arXiv URL To Intake

Biblicus does not fetch URLs for this workflow. Retrieve the paper first, then hand Biblicus one local file plus one metadata file.

Use the arXiv abstract page as `--source-uri`:

```text
https://arxiv.org/abs/<arxiv_id>
```

Store the PDF URL in metadata as `pdf_url`:

```text
https://arxiv.org/pdf/<arxiv_id>
```

Example:

```bash
mkdir -p /tmp/biblicus-intake
curl -L "https://arxiv.org/pdf/2510.07172" \
  -o /tmp/biblicus-intake/arxiv_2510.07172.pdf

$EDITOR /tmp/biblicus-intake/arxiv_2510.07172.biblicus-input.yml

.venv/bin/python -m biblicus research-intake assess \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file /tmp/biblicus-intake/arxiv_2510.07172.biblicus-input.yml \
  /tmp/biblicus-intake/arxiv_2510.07172.pdf
```

If the decision is `accepted` or `pending_review`, ingest through the gate:

```bash
.venv/bin/python -m biblicus research-intake ingest \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file /tmp/biblicus-intake/arxiv_2510.07172.biblicus-input.yml \
  --source-uri https://arxiv.org/abs/2510.07172 \
  /tmp/biblicus-intake/arxiv_2510.07172.pdf
```

If the decision is `rejected`, do not ingest. Include the title, source URI, and decision in the handoff.

For a non-arXiv web article, use the canonical article page as `--source-uri`, store the retrieved HTML or PDF as the local file, set `source_type: web_article`, use the `article` tag instead of `paper`, and write a neutral abstract-like summary because the source may not provide a formal abstract.

For an already-local file, still create the metadata file first. Use the most canonical provenance URL you know as `--source-uri`; if none exists, omit `--source-uri` and explain the missing provenance in the handoff.

## Snapshot Discovery

Use the steering artifact inventory instead of scraping directories:

```bash
.venv/bin/python -m biblicus steering artifacts \
  --corpus corpora/AI-ML-research
```

The output groups stable artifact references by kind, including extraction, retrieval, topic modeling, topic context,
topic governance, topic classifier, and graph artifacts when they exist.

Use more specific list commands when you need a full extractor-specific manifest:

```bash
.venv/bin/python -m biblicus extract list \
  --corpus corpora/AI-ML-research \
  --extractor-id pipeline

.venv/bin/python -m biblicus graph list \
  --corpus corpora/AI-ML-research
```

Do not inspect raw item files or sidecars just to discover snapshots.

## Steering Export

Generate a JSON bundle for an external application steering surface:

```bash
.venv/bin/python -m biblicus steering export \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --topic-governance-snapshot <topic_governance_snapshot_id>
```

This includes catalog item metadata, intake status, the accepted topic set from the seed manifest, governance proposals,
and artifact references. It never includes raw item bytes.

Render a human-accepted application topic set back into a Biblicus classifier seed manifest:

```bash
.venv/bin/python -m biblicus steering render-seed-manifest \
  --input accepted-topic-set.json \
  --output corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json
```

The application owns proposal review state, display copy overrides, ranking hints, publishing order, and permissions.
Biblicus owns the rendered seed manifest and downstream classifier training artifacts.

## Topic Context For Research Agents

Generate a Markdown overview of existing topics and representative examples:

```bash
.venv/bin/python -m biblicus analyze topic-context \
  --corpus corpora/AI-ML-research \
  --topic-modeling-snapshot <topic_modeling_snapshot_id> \
  --max-topics 20 \
  --examples-per-topic 3 \
  --summary-model gpt-5.4-mini \
  --format markdown
```

Use this when arming a research agent before it searches for new material. The report is context only; it does not edit manifests or promote seeds.

The `--summary-model` value is a project-configured OpenAI model string. Do not change it unless the user or repo configuration says to. If model access fails, report that failure instead of silently substituting a different model.

Output shape:

```markdown
# Research Agent Topic Context

- Snapshot: `<topic_context_snapshot_id>`
- Topic modeling snapshot: `<topic_modeling_snapshot_id>`
- Extraction snapshot: `pipeline:<snapshot_id>`
- Topics included: 14
- Examples per topic: 3

## 1. Autonomous AI Scientific Discovery

- Topic ID: `1`
- Documents: 32
- Keywords: Autonomous AI Scientific Discovery
- Guidance: This topic covers AI systems that autonomously perform parts or all of the scientific discovery workflow...

### Representative Examples

#### AI-Researcher: Autonomous Scientific Innovation

- Item ID: `<item-id>`
- Text source: abstract
- Centrality: 0.268
- Source: https://arxiv.org/abs/2505.18705
- Published: 2025-05-24
```

Use the topic headings, guidance, keywords, and examples to steer external research. Do not treat topic-context output as an accepted taxonomy.

## Evidence Search

Query the corpus for a phrase:

```bash
.venv/bin/python -m biblicus query \
  --corpus corpora/AI-ML-research \
  --query "automated scientific discovery agents" \
  --max-total-items 5 \
  --maximum-total-characters 2000
```

If a specific retrieval snapshot is required:

```bash
.venv/bin/python -m biblicus query \
  --corpus corpora/AI-ML-research \
  --snapshot <retrieval_snapshot_id> \
  --retriever <retriever_id> \
  --query "graph rag topic taxonomy"
```

Build a retrieval snapshot when needed:

```bash
.venv/bin/python -m biblicus build \
  --corpus corpora/AI-ML-research \
  --retriever tf-vector \
  --configuration-name ai-ml-research-tf-vector
```

Current practical baseline is `tf-vector`. Dense embedding retrieval exists through embedding-index retrievers, but verify the configured embedding provider before calling it semantic search.

## Inspect A Returned Item

Use `show` for a specific evidence item:

```bash
.venv/bin/python -m biblicus show \
  --corpus corpora/AI-ML-research \
  <item-id>
```

Prefer this over opening raw sidecars directly.

## Research Intake

Assess a local candidate without changing the corpus:

```bash
.venv/bin/python -m biblicus research-intake assess \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  ./paper.pdf
```

Ingest through the gate:

```bash
.venv/bin/python -m biblicus research-intake ingest \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research-v1.1 \
  --configuration configurations/research-intake/ai-ml-research.yml \
  --metadata-file ./paper.biblicus-input.yml \
  --source-uri https://example.org/paper \
  ./paper.pdf
```

Decision meanings:

- `accepted`: stored as an eligible corpus item, not a seed.
- `pending_review`: stored for human review and excluded from topic workflows.
- `rejected`: not stored by intake.

Default AI-ML decision thresholds:

- Accept when a mapped classifier topic exists, classifier score is at least `0.60`, and corpus similarity is at least `0.08`.
- Reject only when corpus similarity is below `0.08` and the classifier is missing, unmapped, or below `0.20`.
- Otherwise mark `pending_review`.

Do not override the decision manually. If a result looks wrong, report the mismatch and ask for curator direction. Only humans or explicitly delegated curator agents should run `research-intake decide`.

List pending items:

```bash
.venv/bin/python -m biblicus research-intake pending \
  --corpus corpora/AI-ML-research \
  --format markdown
```

Only a human or explicitly delegated curator should decide pending items:

```bash
.venv/bin/python -m biblicus research-intake decide \
  --corpus corpora/AI-ML-research \
  --item-id <item-id> \
  --decision accept \
  --topic-uid <topic-uid>
```

## Topic Trends

Run a publication-date-driven trend report:

```bash
.venv/bin/python -m biblicus analyze topic-trends \
  --corpus corpora/AI-ML-research \
  --topic-modeling-snapshot <topic_modeling_snapshot_id> \
  --classifier ai-ml-research-v1.1 \
  --windows 30d,90d,1y,all \
  --format markdown
```

Trend reports use `dates.published_at`, not ingest time. Undated items are excluded and reported as warnings.

## Graph Artifacts

List graph snapshots:

```bash
.venv/bin/python -m biblicus graph list \
  --corpus corpora/AI-ML-research
```

Extract a baseline graph from an extraction snapshot:

```bash
.venv/bin/python -m biblicus graph extract \
  --corpus corpora/AI-ML-research \
  --extractor simple-entities \
  --extraction-snapshot pipeline:<snapshot_id> \
  --configuration configurations/graph/simple-entities.yml
```

Graph extraction creates graph artifacts for later GraphRAG experiments. It is not itself a retrieval query.

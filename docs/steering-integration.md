# Steering integration

Biblicus can power an external application without knowing that application's schema, permissions, user interface, or
publishing rules. The boundary is simple:

- the application owns human decisions and presentation;
- Biblicus owns reproducible corpus processing artifacts.

The steering commands emit JSON contracts that worker agents can import into an application database. They do not
read or write GraphQL, AppSync, Amplify, or any other application-specific surface.

## Commands

Export a steering bundle:

```bash
biblicus steering export \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --topic-governance-snapshot <snapshot_id>
```

The export includes corpus identity, catalog items with full metadata JSON, the accepted topic set from the classifier
seed manifest, normalized steering proposals, recorded proposal bundles, artifact references, and warnings.
It never includes raw item bytes.

List artifact references:

```bash
biblicus steering artifacts \
  --corpus corpora/AI-ML-research
```

This is the supported way for an external worker to discover Biblicus artifacts. It reports extraction, retrieval,
analysis, topic classifier, topic context, topic governance, topic granularity, and graph artifact references when they
exist. It also reports recorded `steering-proposals` artifacts. Missing kinds are represented by empty lists plus warnings.

Render an accepted topic set into a Biblicus seed manifest:

```bash
biblicus steering render-seed-manifest \
  --input accepted-topic-set.json \
  --output corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json
```

The input topic set may include application-only fields such as `subheading`, `aliases`, `editor_notes`, and
`ranking_hints`. Biblicus validates them but does not write them to `seed-manifest.json`.

## Worker flows

### Import corpus state into the application

1. Run `biblicus steering export`.
2. Import `corpus`, `items`, `topic_set`, `proposals`, `artifacts`, and `warnings` into the application's own schema.
3. Preserve the Biblicus `item_id`, `topic_uid`, snapshot identifiers, and artifact references as external identifiers.

### Review governance proposals

1. Use the exported `proposals` list as pending editorial work.
2. Let humans accept, reject, edit, merge, or defer proposals inside the application.
3. Do not write proposal decisions directly into Biblicus artifacts.

### Render accepted topic revisions

1. The application emits an accepted topic-set JSON document.
2. Run `biblicus steering render-seed-manifest`.
3. Train a classifier with `biblicus topic-classifier train`.
4. Run `biblicus steering export` again so the application sees the new artifact references.

### Train the authoritative classifier

The research corpus remains the authoritative taxonomy-training corpus. Once the application has rendered a seed
manifest, a worker trains the classifier in Biblicus:

```bash
biblicus topic-classifier train \
  --corpus corpora/AI-ML-research \
  --manifest corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json \
  --configuration configurations/topic-classifier.yml \
  --extraction-snapshot pipeline:<snapshot_id>
```

### Classify a secondary corpus

Secondary corpora consume the research taxonomy. They do not define their own canonical taxonomy unless a human creates
that policy outside this workflow.

```bash
biblicus topic-classifier project \
  --authority-corpus corpora/AI-ML-research \
  --target-corpus corpora/AI-ML-history \
  --classifier ai-ml-research \
  --format json
```

### Inspect and steer graph artifacts

Workers discover graph, taxonomy, ontology, and steering proposal artifacts through `biblicus steering artifacts`.
Accepted topics do not silently become graph nodes during graph extraction. Biblicus instead separates proposal
generation from accepted graph materialization.

Useful human inputs include:

- accepting or rejecting a discovered topic as a canonical graph entity;
- choosing whether a topic maps to an existing entity or creates a new entity;
- editing graph entity names, descriptions, aliases, and relationship labels;
- approving proposed relationships between topics, people, methods, datasets, benchmarks, and organizations;
- marking graph entities as deprecated or merged without deleting historical artifacts.

Topic-informed graph proposal generation starts with `biblicus steering graph-signals`. Those signals are computational
candidates only. Agents or other workers can turn them into proposal bundles, validate them with
`biblicus steering proposals validate`, and record them with `biblicus steering proposals record`.

Accepted taxonomy and ontology state is materialized explicitly:

```bash
biblicus ontology apply \
  --corpus corpora/AI-ML-research \
  --taxonomy <taxonomy_snapshot_id> \
  --relationships <ontology_snapshot_id> \
  --graph-snapshot simple-entities:<snapshot_id>
```

That command writes deterministic `topic:<topic_uid>` nodes, `subtopic_of` edges, `member_of_topic` edges, and
accepted ontology relationship assertions into Neo4j as an overlay for the selected graph snapshot.

## Accepted topic-set input

The steering application should emit topic-set JSON with this shape:

```json
{
  "schema_version": 1,
  "classifier_id": "ai-ml-research",
  "display_name": "AI/ML Research Topics",
  "description": "Reviewed canonical topics for the AI/ML research corpus.",
  "topics": [
    {
      "topic_uid": "automated-scientific-discovery",
      "display_name": "Automated Scientific Discovery",
      "description": "AI systems that plan, execute, and evaluate scientific discovery workflows.",
      "seed_item_ids": ["11111111-1111-4111-8111-111111111111"],
      "holdout_item_ids": ["22222222-2222-4222-8222-222222222222"],
      "subheading": "Machine agents as scientific collaborators",
      "aliases": ["AI Scientist"],
      "editor_notes": "Display copy is owned by the application.",
      "ranking_hints": {"pinned": false}
    }
  ],
  "unlabeled_policy": "use_minus_one"
}
```

Only `topic_uid`, `display_name`, `description`, `seed_item_ids`, and `holdout_item_ids` are written to the Biblicus
seed manifest.

## External app coding-agent handoff

Treat Biblicus as a worker and artifact provider. Do not scrape directories, raw sidecars, or raw item bytes from the
application worker. Use:

- `biblicus steering export` for import bundles;
- `biblicus steering artifacts` for artifact discovery;
- `biblicus steering graph-signals` for computational graph steering candidates;
- `biblicus steering proposals validate` and `record` for proposal bundle handling;
- `biblicus steering render-seed-manifest` after humans accept topic revisions;
- existing `topic-classifier` commands for training and secondary-corpus projection.

The application schema should model accepted topics, proposal review state, manual display fields, ranking overrides,
and publishing workflows. Biblicus will not store those application-owned records.

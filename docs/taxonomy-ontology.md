# Taxonomy and ontology

Taxonomy and ontology are the reviewed structure that turns topic discovery into graph steering.

## Mental model

The **taxonomy** is a strict topic tree. Root nodes usually come from accepted canonical topics. Child nodes describe
reviewed subtopics under those roots. Each taxonomy node has a stable `topic_uid`, a display name, a description, an
optional parent, and reviewed seed or holdout evidence.

The **ontology** is a graph of typed relationship assertions. Relationship types define domain vocabulary such as
`influenced`, `historical_context_for`, or `use_case_of`. Assertions connect `item:<item_id>`, `topic:<topic_uid>`, and
`graph:<node_id>` references.

Neo4j is a materialized GraphRAG graph. It can include graph extraction output, taxonomy topic nodes, taxonomy
`subtopic_of` edges, item `member_of_topic` edges, and accepted ontology assertions.

## Accepted taxonomy input

The steering application exports accepted taxonomy JSON. Biblicus validates and records it:

```bash
biblicus taxonomy record \
  --corpus corpora/example \
  --input accepted-taxonomy.json
```

Taxonomy input shape:

```json
{
  "schema_version": 1,
  "taxonomy_id": "example-taxonomy",
  "display_name": "Example Taxonomy",
  "description": "Accepted topic hierarchy.",
  "generated_at": "2026-05-16T00:00:00+00:00",
  "nodes": [
    {
      "topic_uid": "agent-systems",
      "parent_topic_uid": null,
      "display_name": "Agent Systems",
      "description": "Research about agent architectures and behaviors.",
      "status": "accepted",
      "seed_item_ids": ["item-one"],
      "holdout_item_ids": []
    },
    {
      "topic_uid": "agent-memory",
      "parent_topic_uid": "agent-systems",
      "display_name": "Agent Memory",
      "description": "Research about memory in agent systems.",
      "status": "accepted",
      "seed_item_ids": ["item-two"],
      "holdout_item_ids": []
    }
  ]
}
```

Biblicus rejects duplicate topic identities, unknown parents, cycles, and unknown fields.

## Taxonomy discovery

Discovery finds possible child nodes under accepted roots:

```bash
biblicus taxonomy discover \
  --corpus corpora/example \
  --classifier example-classifier \
  --extraction-snapshot pipeline:<snapshot_id> \
  --steering-feedback papyrus-steering-feedback.json \
  --format markdown
```

Discovery uses classifier topic membership to collect documents under each accepted root, runs scoped topic modeling for
that root, and emits steering proposals such as `create-taxonomy-node`. It does not mutate the accepted taxonomy.
When `--steering-feedback` is provided, Biblicus validates the Papyrus feedback export and suppresses rejected child-topic
patterns that match the same classifier and root topic. Suppressed candidates are reported as warnings rather than
written as new proposal records.

## Accepted ontology input

The steering application exports accepted relationship types and assertions. Biblicus validates and records them:

```bash
biblicus ontology record \
  --corpus corpora/example \
  --input accepted-ontology.json
```

Ontology input shape:

```json
{
  "schema_version": 1,
  "ontology_id": "example-ontology",
  "display_name": "Example Ontology",
  "description": "Accepted domain relationships.",
  "generated_at": "2026-05-16T00:00:00+00:00",
  "relationship_types": [
    {
      "relationship_uid": "influenced",
      "display_name": "Influenced",
      "description": "The source influenced development of the target.",
      "directed": true
    }
  ],
  "assertions": [
    {
      "assertion_id": "assertion-one",
      "source_ref": "item:item-one",
      "relationship_uid": "influenced",
      "target_ref": "topic:agent-systems",
      "direction": "outbound",
      "evidence_item_ids": ["item-one"],
      "confidence": 0.8
    }
  ]
}
```

## Graph materialization

Materialization is explicit:

```bash
biblicus ontology apply \
  --corpus corpora/example \
  --taxonomy <taxonomy_snapshot_id> \
  --relationships <ontology_snapshot_id> \
  --graph-snapshot simple-entities:<graph_snapshot_id>
```

The command writes deterministic topic nodes, `subtopic_of` edges, item `member_of_topic` edges, and accepted ontology
relationship edges into Neo4j as an ontology overlay for the selected graph snapshot.

Query accepted ontology assertions:

```bash
biblicus ontology query \
  --corpus corpora/example \
  --relationships <ontology_snapshot_id> \
  --source-ref item:item-one \
  --relationship influenced \
  --direction outbound
```

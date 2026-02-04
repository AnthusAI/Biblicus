# Graph Extraction Without a Graph Database

## Summary
This plan defines a graph extraction layer that is fully decoupled from any graph database. The graph is produced as
versioned, sharded snapshot artifacts with a manifest for reproducibility. Incremental updates are supported through
optional local registries and compaction, without requiring a database.

## Principles
- Reproducibility first: graph snapshots are deterministic and rebuildable from the corpus and extraction snapshots.
- Single source of truth: raw corpus + extraction snapshots remain canonical; graphs are derived artifacts.
- Explicit stages: graph extraction is a distinct pipeline stage and does not replace retrieval or analysis.
- No hidden fallbacks: conflicts and inconsistencies are surfaced as explicit errors.

## Scope
In scope:
- Graph extraction snapshot artifacts (nodes, edges, manifest).
- Sharding and manifest contract.
- Optional local registry for incremental updates.

Out of scope:
- Graph algorithms, analysis outputs, or retrieval logic.
- Graph database integration (this remains an optional derived materialization step).

## Terminology
- **Graph extraction**: pipeline stage that produces graph artifacts from extraction snapshots.
- **Graph snapshot**: a versioned artifact set tied to a corpus state and extraction snapshot.
- **Node registry**: local index used only for incremental graph updates.

## Graph Extraction Inputs and Outputs

### Inputs
- Corpus
- Extraction snapshot reference (required for reproducibility)
- Graph extraction configuration

### Outputs
- Snapshot directory under `.biblicus/runs/graph-extract/<snapshot_id>/`
- Sharded node and edge artifacts
- `manifest.json` capturing configuration, provenance, and shard integrity

## Artifact Layout

```
.biblicus/runs/graph-extract/<snapshot_id>/
  manifest.json
  nodes/
    nodes-00001.jsonl
    nodes-00002.jsonl
  edges/
    edges-00001.jsonl
    edges-00002.jsonl
```

## Node and Edge Schema (JSONL)

### Node record
```
{
  "node_id": "item:<item_id>",
  "node_type": "item",
  "properties": {
    "title": "...",
    "tags": ["..."]
  },
  "provenance": {
    "item_id": "<item_id>",
    "source_uri": "file://...",
    "extraction_snapshot": "pipeline:<snapshot_id>"
  }
}
```

### Edge record
```
{
  "edge_id": "item:<item_id>|mentions|entity:<canonical>",
  "src": "item:<item_id>",
  "dst": "entity:<canonical>",
  "edge_type": "mentions",
  "weight": 1.0,
  "properties": {},
  "provenance": {
    "item_id": "<item_id>",
    "extraction_snapshot": "pipeline:<snapshot_id>"
  }
}
```

## Deterministic Identifiers
- Items: `item:<item_id>`
- Segments: `segment:<item_id>:<segment_index>`
- Entities: `entity:<canonical_form>`
- Edge IDs: `src|edge_type|dst|qualifiers`

If the ID exceeds limits, hash the full key and store the original in `properties.key`.

## Sharding Strategy

### Default: Sequential streaming + size rotation
- Sort nodes/edges deterministically (e.g., by ID).
- Write JSONL lines until a size threshold is reached (default 256MB).
- Rotate to the next shard.

### Optional: Hash partitioning
- Assign shard index via `hash(node_id) % N`.
- Used only when stable shard membership is required.

## Manifest Contract

`manifest.json` must include:
- `schema_version`
- `snapshot_id`
- `corpus_uri`
- `catalog_generated_at`
- `extraction_snapshot`
- `graph_config`
- `node_shards` and `edge_shards` (path, line count, byte count, sha256)
- `sharding_policy`
- `generated_at`

## Update Modes

### 1) Snapshot rebuild (default)
- Rebuild the full graph from the extraction snapshot.
- Deterministic output with no external state.

### 2) Append + compact
- Append delta shards for new ingests.
- Periodic compaction merges and deduplicates into a new snapshot.

### 3) Incremental with local node registry
- Maintain a local registry of node IDs to prevent duplicates.
- Registry is a lightweight local store (SQLite or key-value).
- Used to resolve edges to existing nodes without a full rebuild.

## Deduplication Rules

- Nodes dedupe by `node_id`.
- Edges dedupe by `edge_id`.
- If a duplicate `node_id` has conflicting properties, compaction fails with an explicit error.

## Future Graph DB Materialization

Graph databases are treated as derived materialized views:
- Load from shards + manifest.
- Rebuildable on demand.
- Does not change extraction logic or snapshot format.

## Next Steps (Implementation)
- Define BDD specs for graph extraction snapshots.
- Add Pydantic schemas for manifest and node/edge records.
- Implement snapshot builder with sharding and deterministic ordering.
- Add optional registry for incremental updates.

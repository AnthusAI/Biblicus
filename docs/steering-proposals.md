# Steering proposals

Steering proposals separate machine-derived signals from reviewable recommendations. Biblicus
owns the artifact contract; the application owns human decisions.

## Layers

- **Signals** are computational candidates: topic ids, graph snapshot refs, evidence item ids,
  confidence metrics, and deterministic payloads.
- **Proposals** are judgments over signals: `recommend`, `do_not_recommend`, or
  `needs_clarification`.
- **Decisions** are human accept, reject, edit, or defer actions. Biblicus does not write them.

## Graph signals

Generate topic-informed graph signals:

```bash
biblicus steering graph-signals \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --graph-snapshot simple-entities:<snapshot_id> \
  --format json
```

The command emits a proposal bundle with `signals` and an empty `proposals` list. A worker can pass
those signals to an agent, a language model, or a human-authored process.

Every accepted taxonomy topic can produce a signal when the graph snapshot has no known topic entity with
the deterministic node id `topic:<topic_uid>`. Classifier topic maps can also produce candidate
`Item -> Topic` membership edge signals. When an accepted taxonomy artifact exists, graph signals use every
accepted taxonomy node, including child nodes. When no accepted taxonomy artifact exists, graph signals use
the classifier seed manifest as the root-topic source.

## Taxonomy and ontology proposal kinds

Unified steering proposal bundles can now carry topic, graph, taxonomy, and ontology recommendations.
Supported taxonomy and ontology proposal kinds are:

- `create-taxonomy-node`
- `move-taxonomy-node`
- `merge-taxonomy-nodes`
- `split-taxonomy-node`
- `archive-taxonomy-node`
- `add-ontology-relationship`
- `add-relationship-type`

Accepted human decisions still live outside Biblicus. Agents can create proposal bundles with any method,
then validate or record them through the steering proposal commands.

## Sample export

A compact steering export with taxonomy and ontology proposals is available at
`docs/examples/steering-export-taxonomy-ontology.json`.

The sample shows:

- a flattened `proposals` list containing one `create-taxonomy-node` proposal and one
  `add-ontology-relationship` proposal;
- a `proposal_bundles` entry preserving the normalized steering proposal bundle;
- artifact references for `taxonomy`, `taxonomy-discovery`, `ontology`, `steering-proposals`, and
  `graph`;
- the accepted root topic set under `topic_set`.

Accepted taxonomy and ontology manifests are not embedded as top-level steering export fields. The
export carries artifact references to those accepted overlays. Workers can load the referenced
Biblicus artifacts when they need the full accepted taxonomy or ontology assertion manifest.

## Payload field guide

All proposals use the same wrapper fields:

- `proposal_id`: stable proposal identity for idempotent imports;
- `proposal_kind`: one of the supported steering proposal kinds;
- `domain`: `topic` or `graph`;
- `recommendation`: Biblicus or agent judgment, one of `recommend`, `do_not_recommend`, or
  `needs_clarification`;
- `status`: always `proposed` inside Biblicus artifacts;
- `author`: proposal author metadata;
- `source_signal_ids`: computational signal identifiers that support the proposal;
- `evidence`: proposal-level evidence, usually including `item_ids`;
- `rationale`: human-readable reason for the recommendation;
- `confidence`: optional proposal confidence;
- `payload`: proposal-kind-specific contract.

`recommend`, `do_not_recommend`, and `needs_clarification` are not human review actions. They are
proposal recommendation labels authored before human review. External applications should keep their
own human actions, such as accept, reject, edit, or defer, in application-owned decision records.

### `create-taxonomy-node`

Use when discovery suggests a new accepted taxonomy node.

Expected payload fields:

- `topic_uid`: proposed stable topic identity;
- `parent_topic_uid`: parent topic identity, or `null` when proposing a root;
- `display_name`: proposed topic label;
- `description`: proposed topic description;
- `document_ids`: supporting documents from scoped discovery;
- `keywords`: representative topic keywords;
- `topic_id`: source BERTopic integer topic id, when applicable.

### `move-taxonomy-node`

Use when a taxonomy node appears to belong under a different parent.

Expected payload fields:

- `topic_uid`: topic identity to move;
- `current_parent_topic_uid`: current parent identity, or `null`;
- `proposed_parent_topic_uid`: proposed parent identity, or `null`;
- `evidence_item_ids`: evidence supporting the move.

### `merge-taxonomy-nodes`

Use when two or more taxonomy nodes appear semantically redundant.

Expected payload fields:

- `source_topic_uids`: topic identities proposed for merging;
- `target_topic_uid`: surviving topic identity;
- `display_name`: proposed surviving display name, when a rename is suggested;
- `description`: proposed surviving description, when a rewrite is suggested;
- `evidence_item_ids`: evidence supporting the merge.

### `split-taxonomy-node`

Use when one taxonomy node repeatedly contains multiple stable child concepts.

Expected payload fields:

- `topic_uid`: topic identity proposed for splitting;
- `proposed_children`: list of child topic objects, each with `topic_uid`, `display_name`,
  `description`, and optional `seed_item_ids` or `holdout_item_ids`;
- `evidence_item_ids`: evidence supporting the split.

### `archive-taxonomy-node`

Use when a taxonomy node no longer has active analytical value.

Expected payload fields:

- `topic_uid`: topic identity proposed for archiving;
- `reason`: archive rationale;
- `evidence_item_ids`: evidence supporting the archive decision.

### `add-ontology-relationship`

Use when an accepted typed relationship assertion should be added.

Expected payload fields:

- `assertion_id`: stable assertion identity for idempotent imports and accepted ontology manifests;
- `source_ref`: source reference, using `item:<item_id>`, `topic:<topic_uid>`, or
  `graph:<node_id>`;
- `relationship_uid`: relationship type identity, such as `influenced`,
  `historical_context_for`, or `use_case_of`;
- `target_ref`: target reference, using the same ref vocabulary as `source_ref`;
- `direction`: `outbound` or `inbound`;
- `evidence_item_ids`: evidence item identifiers;
- `confidence`: optional assertion confidence;
- `notes`: optional reviewer or agent note.

When accepted, these fields can be rendered directly into an ontology assertion manifest.

### `add-relationship-type`

Use when a new reusable relationship predicate is needed.

Expected payload fields:

- `relationship_uid`: stable relationship type identity;
- `display_name`: human-readable relationship name;
- `description`: relationship definition;
- `directed`: whether assertions using this relationship are directed.

### Deprecated or suppressing graph structure

Use `suppress-entity-or-edge` for graph entities or edges that should be hidden, ignored, or
excluded from a future graph view or materialization step. This remains a proposal only; Biblicus does
not remove graph data automatically.

## Proposal bundles

Validate an externally authored proposal bundle:

```bash
biblicus steering proposals validate \
  --input proposal-bundle.json
```

Record a validated bundle as a reproducible Biblicus artifact:

```bash
biblicus steering proposals record \
  --corpus corpora/AI-ML-research \
  --input proposal-bundle.json
```

Recorded bundles are written under:

```text
analysis/steering-proposals/<snapshot_id>/
```

The directory contains:

- `manifest.json`: reproducibility metadata and artifact paths;
- `signals.json`: computational signal records;
- `proposals.json`: proposal judgments;
- `report.md`: optional human-readable rendering when available.

## Proposal recommendations

Proposals must use one of:

- `recommend`
- `do_not_recommend`
- `needs_clarification`

Negative recommendations are first-class. Applications should show them because they explain what
the agent considered and rejected.

## Human decisions

The external steering application imports proposal artifacts and records human decisions in its own
schema. Biblicus proposal artifacts must not contain human decision fields or accepted/rejected
review state.

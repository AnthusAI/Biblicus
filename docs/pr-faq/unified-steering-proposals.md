# Unified Steering Proposals

## Press Release

Biblicus now has one proposal contract for topic and graph steering. Workers can export
computational signals, validate externally authored proposal judgments, and record immutable
proposal artifacts without Biblicus knowing whether those judgments came from deterministic code,
an agent, a language model, or a person.

## Frequently Asked Questions

### What are the steering layers?

The first layer is computational signals: metrics, identifiers, graph snapshot references,
classifier mappings, and evidence item identifiers. The second layer is proposal judgment:
`recommend`, `do_not_recommend`, or `needs_clarification`. The third layer is the human decision,
which stays in the external application.

### Does Biblicus call a language model?

No. Biblicus validates and records proposal artifacts. External workers or agents may read
`signals.json`, create proposal bundles however they choose, and ask Biblicus to validate or
record those bundles.

### Does graph steering mutate graph snapshots?

No. The first pass is proposals-only. Biblicus can signal that an accepted topic should have a
graph entity such as `topic:<topic_uid>`, but accepting or applying that proposal belongs to the
steering application and a later graph-writing workflow.

### How are topic and graph proposals unified?

Both use `SteeringProposal`. Topic trend governance now emits general topic-domain proposals.
Graph steering emits graph-domain signals and accepts graph-domain proposal kinds such as
`create-topic-entity`, `map-topic-to-entity`, `add-topic-membership-edge`, and
`suppress-entity-or-edge`.

### Where do proposal artifacts live?

Recorded proposal bundles live under `analysis/steering-proposals/<snapshot_id>/` with
`manifest.json`, `signals.json`, and `proposals.json`. `biblicus steering export` includes the
latest normalized proposal records for application import.

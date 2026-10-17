# Steering Integration

## Press Release

Biblicus now exposes a stable steering contract for external applications. An application can import corpus state,
artifact references, reviewed topic definitions, and governance proposals without scraping Biblicus directories or
depending on Biblicus to know anything about its GraphQL schema.

## Frequently Asked Questions

### What does Biblicus own?

Biblicus owns corpus processing artifacts: raw item identity, catalog metadata, extraction snapshots, retrieval
snapshots, topic-modeling outputs, topic context reports, topic governance proposals, topic classifier manifests, and
graph extraction artifacts.

### What does the external application own?

The external application owns users, permissions, editorial workflow, publishing order, manual ranking overrides,
display copy edits, and accepted human decisions. Biblicus can draft proposals, but it does not publish or accept them.

### Is Biblicus depending on GraphQL, AppSync, or Amplify?

No. The contract is JSON emitted by command-line commands. The external application decides how to map that JSON into
its own schema.

### Does this connect topic modeling to GraphRAG?

Partially. Biblicus can expose graph artifacts and generate topic-informed graph steering signals. Topic-modeled
categories still do not automatically become graph entities. Workers record proposal bundles, and human decisions remain
in the steering application.

### How does the application discover artifacts?

It runs `biblicus steering artifacts`. That command returns deterministic artifact references for supported
Biblicus artifact kinds instead of requiring worker-side directory scraping.

### How does a human-approved topic set get back into Biblicus?

The application exports an accepted topic-set JSON document. `biblicus steering render-seed-manifest` validates
that input and writes a strict Biblicus topic classifier `seed-manifest.json`. Training still happens through
`biblicus topic-classifier train`.

### Do governance proposals mutate accepted topics?

No. Proposals are imported into the steering application as pending editorial records. Accepted topic changes become real only
when the external application emits an accepted topic-set JSON document and Biblicus renders a new seed manifest from it.

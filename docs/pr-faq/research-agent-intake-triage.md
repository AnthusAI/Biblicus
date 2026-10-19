# Research Agent Intake Triage

## Press Release

Biblicus now gives research agents a pre-ingest relevance gate. Agents can assess a local candidate item from curated
metadata before storing it, then let Biblicus decide whether the item is accepted, rejected, or stored as
`pending_review` for a later human decision.

## Frequently Asked Questions

### Is this a new retrieval or download system?

No. Research agents still retrieve files and metadata outside Biblicus. Intake reads a local file path and a metadata
file, using `title` and `abstract` as the assessment text.

### What are the decisions?

`accepted` means the item fits an existing reviewed topic well enough to become an eligible corpus item. `pending_review`
means the item may be relevant but needs a human decision before it influences topic modeling. `rejected` means Biblicus
does not ingest the item.

### Where do pending items live?

Pending items live in the same corpus as ordinary items, with `curation.intake_status: pending_review` and an
`intake_assessment` block in their sidecar metadata. Topic modeling and topic classifier training exclude pending and
rejected items by default.

### Does intake create new seed topics?

No. Intake records evidence and a decision. It does not promote predictions into seeds, edit seed manifests, or accept a
new topic on its own.

### How does a human approve a pending item?

Curators can update the decision with `biblicus research-intake decide`. A later dashboard can call the same information
workflow instead of inventing separate metadata semantics.

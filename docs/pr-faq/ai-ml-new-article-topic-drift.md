# AI-ML-Research New Article Topic Drift Pilot

## Press Release

Biblicus now gives AI-ML-Research curators a repeatable way to review newly ingested topic candidates before changing
the reviewed topic classifier. A research agent can add articles through the standard single-item ingest command, then
curators can run a blind batch review that compares the current classifier prediction with unsupervised topic discovery.

## Frequently Asked Questions

### Is this a new ingest pathway?

No. New articles still arrive through the standard local-file ingest command. The batch review reads catalog metadata
that already exists: tags, source provenance, and `curation.proposed_topic_uid`.

### Does the review command train the classifier?

No. The review command classifies candidate items with the current trained model and joins those predictions to an
exploratory topic modeling snapshot. It produces review rows; it does not promote predictions into seeds.

### How are classifier versions handled?

The human-facing classifier identity should stay stable. Reproducibility comes from the automatic model version hash
written by training. If curators draft a revised seed manifest, training that manifest produces a new automatic model
version without requiring people to manually increment names.

### When should curators revisit the topic list?

After every research-agent batch, and earlier when the batch shows topic drift signals: many unmapped classifier
predictions, many low-confidence predictions, or a candidate topic with enough examples to review.

### How does a reviewed candidate become a topic?

Curators use the batch review rows to choose seed-quality and holdout-quality examples. Biblicus can draft a new
manifest file from the current manifest plus one reviewed topic, leaving the baseline manifest unchanged.

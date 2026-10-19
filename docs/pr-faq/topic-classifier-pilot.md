# PR-FAQ: Topic Classifier Pilot

## Press Release

Biblicus is introducing a topic classifier workflow for corpora that already have a curated set of example items. The
first pilot targets `corpora/AI-ML-research` and stores classifier seed labels in a strict manifest instead of moving
files into topic folders. The manifest points to stable Biblicus item identifiers, separates seed exemplars from
holdouts, and leaves every unlisted item unlabeled.

This workflow turns BERTopic's semi-supervised mode into a reproducible classifier-style artifact. Seed labels guide
training, but BERTopic still assigns its own integer topic identifiers and can discover topics that do not map back to a
seed label. Biblicus stores those BERTopic identifiers only inside a model version and maps them back to stable
`topic_uid` values for user-facing output.

## Customer FAQ

**Who is this for?**

Users who have a corpus with a small number of reviewed exemplars per topic and want repeatable, immediate topic
classification for existing or newly ingested items.

**Why use a manifest instead of folders?**

The raw corpus remains the single source of truth. A classifier manifest can label seed and holdout items by identifier
without changing file layout, duplicating content, or mixing modeling state into item sidecars.

**Is this replacing exploratory topic modeling?**

No. `biblicus analyze topics` remains the exploratory clustering workflow. `biblicus topic-classifier` is a separate
workflow that starts from a seed manifest and produces classifier model versions.

**Are BERTopic topic IDs stable?**

No. BERTopic topic IDs are integers scoped to one model version. Biblicus uses manifest `topic_uid` values as the stable
classifier topic identities and records a per-version topic map from BERTopic IDs to those identities.

**Can a seed topic split across multiple BERTopic topics?**

Yes. If seed exemplars for one `topic_uid` land in multiple BERTopic topic IDs, the topic map records all of those IDs
for the same Biblicus topic.

**What happens to unknown topics?**

BERTopic topics with no seed majority are recorded as discovered topics. Classification for those topics returns no
seed `topic_uid` and recommends review.

**Does a new classified item become a seed automatically?**

No. Predictions are not promoted into seeds. Learning happens by editing the seed manifest or adding reviewed labels,
then training a new model version.

## Implementation Notes

The pilot stores `seed-manifest.json` under
`corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/`. Training reads all catalog items from the
configured extraction snapshot. Seed exemplars receive internal numeric class labels, while holdouts and unlisted items
receive `-1`.

Training writes versioned artifacts under `analysis/topic-classifier/<model_version>/`:

- `model-manifest.json`
- `topic-map.json`
- `holdout-evaluation.json`
- a persisted BERTopic model directory

Classification loads the latest model version for the classifier and returns JSON with the item identifier, model
version, BERTopic topic ID, mapped `topic_uid` when one exists, confidence when BERTopic provides it, review status, and
representative evidence.

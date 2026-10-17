# Topic classifier

Biblicus topic classifiers are classifier-style analysis artifacts built from a strict seed manifest. They are separate
from exploratory topic modeling: `biblicus analyze topics` discovers and labels clusters, while
`biblicus topic-classifier` starts from reviewed seed exemplars and produces a reusable model version for classification.

## Manifest labels

Classifier labels live in one manifest under the corpus metadata directory:

```text
metadata/topic-classifiers/<classifier_id>/seed-manifest.json
```

The manifest references stable item identifiers from item sidecars. It does not move files and does not edit item
metadata. The required fields are:

- `schema_version`: manifest schema version, currently `1`.
- `classifier_id`: stable classifier identifier.
- `display_name`: human-readable classifier name.
- `description`: classifier purpose.
- `topics`: reviewed topic definitions.
- `unlabeled_policy`: currently `use_minus_one`.

Each topic contains:

- `topic_uid`: stable Biblicus topic identity.
- `display_name`: human-readable topic name.
- `description`: topic definition.
- `seed_item_ids`: item identifiers used as supervised exemplars.
- `holdout_item_ids`: reviewed examples withheld from supervision for evaluation.

Unknown fields are errors. Duplicate `topic_uid` values, unknown item identifiers, seed reuse across topics, and
seed/holdout overlap are errors.

## Training

Train a classifier with:

```bash
biblicus topic-classifier train \
  --corpus corpora/AI-ML-research \
  --manifest corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json \
  --configuration configurations/topic-classifier.yml \
  --configuration-name ai-ml-research \
  --extraction-snapshot pipeline:<snapshot_id>
```

Training uses all extracted catalog items. Seed exemplars receive an internal numeric class label derived from the
manifest topic order. Holdouts and all unlisted items receive `-1`, which tells BERTopic they are unlabeled. These
labels guide BERTopic; they do not force final topic IDs.

Training writes a model version under:

```text
analysis/topic-classifier/<model_version>/
```

The directory contains:

- `model-manifest.json`: reproducibility metadata, classifier inputs, and training summary.
- `topic-map.json`: mapping from BERTopic integer topic IDs to stable Biblicus `topic_uid` values.
- `holdout-evaluation.json`: holdout predictions and aggregate review counts.
- `model/`: persisted BERTopic model.

BERTopic integer topic IDs are model-version-local. Biblicus maps them back to manifest `topic_uid` values by majority
seed membership. If one seed topic splits across multiple BERTopic IDs, every split ID maps to the same `topic_uid`. A
BERTopic topic with no seed majority is recorded as discovered.

## Classification

Classify an existing corpus item with:

```bash
biblicus topic-classifier classify \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --item-id <item_id>
```

The command loads the latest model version for the classifier, extracts text for the item from the model's recorded
extraction snapshot, transforms the item with BERTopic, and returns JSON containing:

- `item_id`
- `model_version`
- `bertopic_topic_id`
- `topic_uid`
- `display_name`
- `score`
- `review_recommended`
- `representative_evidence`
- `topic_candidates`

`topic_candidates` is a ranked list of mapped candidate topics. If the best mapped score is below the review threshold,
`topic_uid` and `display_name` are `null`, `review_recommended` is true, and the ranked candidates remain available for
human review.

## Ingest and classify one item

Classify a new source in one command:

```bash
biblicus topic-classifier ingest-classify \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  ./new-paper.pdf
```

This command ingests the source, reindexes the corpus, extracts text for the new item using the model's recorded
extraction snapshot reference, and classifies it with the current model. Predictions are not recorded unless `--record`
is passed. Recorded predictions are audit records, not new seeds.

## Parameter changes

Significant BERTopic parameter changes create a new model version from the corpus and manifest. Representation-level
changes such as display labels or descriptions belong in the manifest and documentation, not in the persisted BERTopic
topic IDs. New learning should be expressed through reviewed seed or holdout updates followed by a new training run.
The human-facing classifier identity should remain stable; training writes an automatic model version hash for
reproducibility, so curators do not need to manually increment classifier names.

## New article topic review

Newly ingested articles can be reviewed as a blind candidate batch before changing the seed manifest:

```bash
biblicus topic-classifier review-batch \
  --corpus corpora/AI-ML-research \
  --classifier ai-ml-research \
  --extraction-snapshot pipeline:<snapshot_id> \
  --topic-modeling-snapshot <topic_modeling_snapshot_id> \
  --candidate-tag automated-scientific-discovery-candidate \
  --proposed-topic-uid automated-scientific-discovery \
  --format markdown
```

The command selects catalog items whose tags and `curation.proposed_topic_uid` match the requested candidate batch. It
classifies those items with the current trained classifier, joins each item to the exploratory topic modeling snapshot,
and emits review rows containing the item identifier, title, source, proposed topic, classifier prediction, score, review
recommendation, unsupervised topic identifier, topic keywords, and a `pending` reviewer decision.

Use `--record` only when the predictions should be appended to the classifier audit log. Recorded predictions are still
not seeds.

The report summary includes standing topic-management signals:

- review after every non-empty batch;
- review immediately when more than fifteen percent of the batch is unmapped by the classifier;
- review immediately when more than twenty-five percent of the batch is low-confidence or review-recommended;
- review a candidate topic when it reaches at least five candidate items.

After human review, draft a revised manifest without changing the baseline file:

```bash
biblicus topic-classifier draft-manifest \
  --base-manifest corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json \
  --output corpora/AI-ML-research/metadata/topic-classifiers/review-drafts/automated-scientific-discovery.json \
  --topic-uid automated-scientific-discovery \
  --topic-display-name "Automated Scientific Discovery" \
  --topic-description "Reviewed articles about agents and systems that automate scientific research." \
  --seed-item-id <seed_item_id> \
  --seed-item-id <seed_item_id> \
  --seed-item-id <seed_item_id> \
  --holdout-item-id <holdout_item_id>
```

Omitting `--classifier-id` preserves the base classifier identity. Training the drafted manifest creates a new automatic
model version hash.

## AI-ML Research authority

The `ai-ml-research` classifier uses a stable human-facing classifier identifier and automatic model version hashes.
It is trained only from the research corpus. Article-format AI/ML history captures belong in `corpora/AI-ML-history`
and are classified by projection rather than used as seed examples.

Build the mixed PDF and HTML extraction recipe before training:

```bash
biblicus extract build \
  --corpus corpora/AI-ML-research \
  --configuration configurations/extraction/ai-ml-research-topic-text.yml \
  --configuration-name ai-ml-research-topic-text \
  --force
```

The recipe keeps Markdown and plain text on `pass-through-text`, extracts PDFs with `pdf-text`, converts HTML with
`markitdown`, and uses `select-override` so `text/html` and `application/xhtml+xml` items use the MarkItDown output.
Use `--force` when changing or validating extraction semantics so older raw HTML artifacts cannot be reused.

After extraction, train the classifier with the canonical seed manifest:

```bash
biblicus topic-classifier train \
  --corpus corpora/AI-ML-research \
  --manifest corpora/AI-ML-research/metadata/topic-classifiers/ai-ml-research/seed-manifest.json \
  --configuration configurations/topic-classifier.yml \
  --configuration-name ai-ml-research \
  --extraction-snapshot pipeline:<snapshot_id>
```

## Projecting To Related Corpora

Use projection when another corpus should receive topic predictions from the research authority without contributing
training examples. The target corpus must have its own extraction snapshot, and records are written only to the target
corpus when `--record` is passed.

For AI/ML history articles:

```bash
biblicus extract build \
  --corpus corpora/AI-ML-history \
  --configuration configurations/extraction/ai-ml-research-topic-text.yml \
  --configuration-name ai-ml-history-topic-text
```

Then project the canonical classifier:

```bash
biblicus topic-classifier project \
  --classifier-corpus corpora/AI-ML-research \
  --target-corpus corpora/AI-ML-history \
  --classifier ai-ml-research \
  --extraction-snapshot pipeline:<history_snapshot_id> \
  --all \
  --top-k 5 \
  --record \
  --format markdown
```

Projection output includes a primary topic only when the best mapped candidate clears the review threshold. Otherwise
`topic_uid` and `display_name` are `null`, `review_recommended` is true, and `topic_candidates` carries the ranked
candidate list for human review. This is expected for journalistic or historical articles that span multiple research
themes.

`--item-id` is repeatable for targeted projection batches. `--all` projects every catalog item that is represented by
the target extraction snapshot. If an item has no extracted text, empty extracted text, or text shorter than the
classifier configuration allows, Biblicus records that row in `skipped_items` and continues the batch. Skipped items are
audit output only; they are not recorded as projections even when `--record` is passed.

The AI/ML history corpus is projection-only for this classifier. Do not train `ai-ml-research` from history articles,
do not add history article ids to the research seed manifest, and do not reintroduce `machine-learning-history` as a
research authority topic.

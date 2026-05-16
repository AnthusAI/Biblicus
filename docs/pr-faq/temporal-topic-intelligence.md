# Temporal Topic Intelligence PR-FAQ

## Press Release

Biblicus now distinguishes durable knowledge-base topics from publication-date-driven trending topics. Corpus curators can run a reproducible topic trend report over an existing topic modeling snapshot, see which clusters are gaining momentum by publication date, and receive proposal artifacts for taxonomy changes without silently changing the accepted topic classifier manifest.

## FAQ

### Why use publication date instead of ingest date?

Trend analysis should describe the original content, not the day a corpus was backfilled. Biblicus uses `dates.published_at` as the trend clock. Items without that field remain searchable and classifiable, but they are excluded from trend metrics with warnings.

### What changes automatically?

Trend reports, momentum rankings, and governance proposals are generated automatically. Accepted canonical topics do not change automatically. Proposals are stored as review artifacts that can be accepted later by drafting a reviewed classifier manifest.

### How are topics ranked?

The first ranking is momentum: a topic's share inside a recent publication window divided by its all-time corpus share. This surfaces emerging clusters without confusing them with historically large topics.

### Where do proposals live?

The analysis writes immutable artifacts under `analysis/topic-governance/<snapshot_id>/`. The proposals are evidence records, not decisions. Human decisions and drafted manifests live separately under corpus metadata.

### What is not included?

This does not add a dashboard view, does not use ingest time for trend metrics, and does not automatically promote proposals into seeds or accepted taxonomy changes.

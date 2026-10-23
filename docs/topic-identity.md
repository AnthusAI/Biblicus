# Topic identity

BERTopic numbers its clusters from zero on every run, so "cluster 41" in this week's run has nothing to do with "cluster 41" last week. Topic identity matches the clusters of a run to the clusters of the previous run, assigns each cluster a stable `uid` that is carried forward, and reports what happened to it: `new`, `continued`, `merged`, `split`, or `gone`.

Biblicus supplies identity and statistics only. Naming a cluster, accepting it, and deciding what to publish belong to the consumer, which keys its own state on the `uid`.

## Run it

Run topic modeling first, then identify the run. The first run has no previous run:

```bash
biblicus analyze topics --corpus corpora/AI-ML-research ...                    # produces <run_a>
biblicus analyze topic-identity --corpus corpora/AI-ML-research --current <run_a>
```

Every later run is matched to the run before it:

```bash
biblicus analyze topic-identity \
  --corpus corpora/AI-ML-research \
  --current <run_b> \
  --previous <run_a> \
  --threshold 0.5
```

- `--current` is the topic modeling snapshot identifier to identify (the `snapshot.snapshot_id` of `biblicus analyze topics`).
- `--previous` is the previous topic modeling snapshot. It must already have been identified, because stable identifiers are carried forward from its identity report. A missing report is an error that tells you which command to run first.
- `--threshold` is the minimum Jaccard overlap of member item identifiers for two clusters to match. It must be greater than 0 and at most 1, and defaults to 0.5.
- `--trends-snapshot` optionally names a `topic-trends` snapshot built with `--bin weekly --weeks 8` or more for the same `--current` run. Each cluster then carries its 8-week series. See [Topic trends](topic-trends.md).
- `--format json` (default) or `markdown` selects the standard output rendering. The JSON file is written either way.

## How clusters are matched

Jaccard overlap is the number of shared item identifiers divided by the number of distinct item identifiers in either cluster. Every pair of a previous cluster and a current cluster whose overlap reaches the threshold is a match. The outlier topic (`-1`) is not a cluster and is never matched.

Each previous `uid` is carried to at most one current cluster: matches are taken in order of highest overlap, then previous `uid`, then current topic identifier, and a previous cluster or a current cluster is used once. Current clusters left without a carried `uid` get a new one, `cl-` followed by the first 12 characters of the SHA-256 of `<run id>:<topic id>` for the run in which they first appear. The same two runs and threshold always give the same identifiers and events.

| Event | When | `uid` |
| --- | --- | --- |
| `new` | no previous cluster overlaps it | new, derived from this run and topic |
| `continued` | exactly one previous cluster overlaps it and that cluster overlaps nothing else | the previous `uid` |
| `merged` | two or more previous clusters overlap it | the `uid` of its best-overlapping predecessor if still free, otherwise new |
| `split` | exactly one previous cluster overlaps it, and that cluster also overlaps other current clusters | the best-overlapping successor keeps the previous `uid`; the others get new ones |
| `gone` | a previous cluster no current cluster overlaps | listed under `gone`, not under `clusters` |

`predecessor_uids` lists every overlapping previous cluster. For a `split`, `successor_uids` lists the `uid` of every current cluster that descends from the same predecessor, including the cluster itself.

`first_seen` is the date of the first run that contained the cluster. It is the date part of that run's `generated_at`, carried forward through `continued`, `merged` (the earliest predecessor) and `split`. `earliest_published_at` is the earliest `dates.published_at` among the member items, so a consumer can tell a cluster that is new to the pipeline from one that is new to the world.

## Output

The report is written to:

```text
analysis/topic-identity/<current run id>/output.json
```

and is the standard output of the command. It is a `TopicIdentityOutput`; the published schema is `docs/api-schemas/analyze-topic-identity.response.schema.json` and the request schema is `analyze-topic-identity.request.schema.json`. Re-running the same command overwrites the file with identical content.

```json
{
  "schema_version": 1,
  "analysis_id": "topic-identity",
  "run_id": "<current run id>",
  "previous_run_id": "<previous run id>",
  "generated_at": "2026-09-08T00:00:00+00:00",
  "threshold": 0.5,
  "trends_snapshot_id": null,
  "series_iso_weeks": null,
  "document_count": 26,
  "outlier_document_count": 6,
  "cluster_count": 1,
  "event_counts": {"new": 0, "continued": 1, "merged": 0, "split": 0, "gone": 1},
  "clusters": [
    {
      "uid": "cl-1f3a9c0b27d4",
      "topic_id": 4,
      "event": "continued",
      "predecessor_uids": ["cl-1f3a9c0b27d4"],
      "successor_uids": [],
      "label": "Agent Reliability",
      "top_terms": ["agent", "reliability"],
      "member_item_count": 20,
      "member_item_ids": ["..."],
      "first_seen": "2026-09-01",
      "earliest_published_at": "2026-03-02",
      "weekly_series": null
    }
  ],
  "gone": [
    {
      "uid": "cl-77aa01c3be90",
      "label": "Old Topic",
      "top_terms": ["omega"],
      "member_item_count": 11,
      "first_seen": "2026-09-01",
      "last_seen_run_id": "<previous run id>"
    }
  ],
  "artifact_paths": {"output": "/path/to/analysis/topic-identity/<run>/output.json"}
}
```

Field notes:

- `top_terms` holds up to 10 topic keywords in rank order; `member_item_ids` is sorted; `member_item_count` equals its length.
- `weekly_series` is `null` unless `--trends-snapshot` is given. When given, it is the last 8 weekly counts of the cluster's topic, oldest to newest, and `series_iso_weeks` lists the 8 matching ISO week labels. The trends snapshot must have been built from the same `--current` run with `--bin weekly` and at least 8 weeks, otherwise the command fails with a message saying so.
- `document_count`, `outlier_document_count` and `cluster_count` record the size of the run. Growing, cooling and new-cluster labels are a front-end rule applied only after four or more weeks of series data; Biblicus does not compute them.
- `event` is one of `new`, `continued`, `merged`, `split`.

## Corpus size

BERTopic needs a reasonable corpus before its clusters stay put between runs. With too few documents clusters appear and vanish, which shows up here as spurious `new` and `gone` events. Record, for each corpus you track, the smallest `document_count` at which events were stable, and treat runs below it as unreliable. See [Topic modeling](topic-modeling.md).

## Behavior specifications

`features/topic_identity.feature` specifies a continuing cluster, the first run, a new cluster, a merge, a split, a disappearing cluster, determinism, the threshold, carry-forward across three runs, reported statistics and corpus size, the failure cases, Markdown output, and the weekly series.

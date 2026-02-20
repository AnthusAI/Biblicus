# Collections

Collections mirror remote storage roots and materialize **one corpus per discovered subfolder**. They are the
canonical way to handle remote sources that contain many evolving folders, such as prospect buckets where each
prospect is a folder.

A collection is **one-way mirror** only. Remote is authoritative; local corpora are updated and pruned to match.

## When to use collections
Use collections when:
- A remote root contains many subfolders that should each be their own corpus.
- New subfolders appear over time and must become corpora automatically.
- You need to mirror multiple providers and accounts in the same project.

## Collection layout
Collections live under `collections/<name>/metadata/config.json`.
Corpora created by the collection live under `corpora/<collection>/<subfolder>/`.

Example structure:
```
collections/
  nexus/
    metadata/
      config.json
corpora/
  nexus/
    catalyst/
      metadata/
        config.json
    acme/
      metadata/
        config.json
```

## Example collection config
```json
{
  "schema_version": 1,
  "created_at": "2026-02-20T00:00:00Z",
  "collection_name": "nexus",
  "source": {
    "kind": "azure-blob",
    "profile": "azure-prod",
    "container": "nexus",
    "prefix": ""
  },
  "discovery": {
    "mode": "subfolder",
    "depth": 1,
    "include_root_files": false
  },
  "corpus_root": "corpora/nexus",
  "auto_create": true,
  "deletion_policy": "archive"
}
```

## Mirroring a collection
```
python -m biblicus collection pull --collection collections/nexus
```

This discovers subfolders, creates corpora for new ones, and mirrors content for all corpora.
Corpora missing from the remote are moved under `corpora/<collection>/.archived/` when `deletion_policy` is `archive`.

## Partitioned tables (optional)
If you want subfolders to represent **tables** inside a single corpus, set a partition rule in the corpus config.
Items will be tagged with the table name in metadata instead of creating new corpora.

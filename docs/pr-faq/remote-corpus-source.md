# PR-FAQ: Remote Corpus Source (Authoritative Mirror) (Draft)

## Press Release

Today we are introducing remote corpus sources for Biblicus. A corpus can now be configured to mirror an S3 bucket or Azure Blob container as its authoritative source. Running `biblicus source pull` downloads remote objects into the local corpus, updates items when the remote changes, and prunes local items that no longer exist remotely. This keeps the corpus deterministic, reproducible, and ready for extraction, retrieval, and analysis using the existing Biblicus workflows.

Remote sources are one-way by design. Biblicus materializes remote content into the corpus so that evidence, snapshots, and metadata remain stable and inspectable on disk. Credentials are handled through the existing user configuration file (`~/.biblicus/config.yml` or `./.biblicus/config.yml`) with environment variables taking precedence.

## FAQ

**Why remote sources?**
Many teams store raw content in S3 or Azure Blob. Remote sources make that content a first-class Biblicus corpus without changing downstream extraction and retrieval workflows.

**Is this a sync tool?**
No. This is a one-way, authoritative mirror. Biblicus pulls from remote storage into a local corpus and never pushes local edits back upstream.

**What happens when remote content changes?**
On `source pull`, Biblicus updates local items when the remote object changes (via ETag or last-modified) and prunes local items that no longer exist remotely.

**Can I still use `biblicus ingest` or `import-tree`?**
Not when a remote source is configured. Local ingest is blocked to avoid divergence. Use `biblicus source pull` to refresh the corpus.

**Where is the configuration stored?**
Corpus-level configuration lives in `metadata/config.json`. Remote source settings are stored there under a `source` block.

**How do credentials work?**
Credentials come from the existing Biblicus user config system:
1) `~/.biblicus/config.yml`
2) `./.biblicus/config.yml`

Environment variables override config values.

**Which providers are supported?**
Version zero supports:
- Amazon S3 (`s3://bucket/key`)
- Azure Blob Storage (`azure-blob://account/container/blob`)

**What about partial mirrors?**
Use a `prefix` to scope the mirror to a subtree within the bucket/container.

**Does this change snapshot reproducibility?**
No. Remote content is materialized into the corpus and then processed by the existing snapshot system. The local corpus remains the source of truth for derived artifacts.

**What if the SDKs are missing?**
Biblicus will fail with a clear error that includes the extra to install (for example, `pip install "biblicus[aws]"` or `pip install "biblicus[azure]"`).

**Is there a plan for bidirectional sync?**
No. The design is intentionally one-way to keep the corpus deterministic and avoid hidden divergence.

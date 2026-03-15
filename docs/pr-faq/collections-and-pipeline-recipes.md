## PR-FAQ: Collections and Pipeline Recipes

### Summary
We are introducing **collections** and **pipeline recipes** to make remote corpora scalable, explicit, and repeatable.
Collections mirror remote storage roots and materialize **one corpus per discovered subfolder** (for example, one
prospect per folder). Pipeline recipes provide a single YAML file that declares the corpus (or collection selector)
and the extraction, retrieval, and analysis steps to run.

This keeps the system explicit and reproducible while supporting many sources (S3, Azure Blob, FTP, HTTP, zip)
and many corpora at once without manual bookkeeping.

### Why are we doing this?
- We need a **one-way mirror** from remote roots that grow over time.
- We need to treat each discovered folder as its **own corpus** without manual initialization.
- We need a **single, readable recipe** that runs the full pipeline for a corpus or a subset of a collection.
- We must support **many different remote sources** and credentials at once.

### What is a collection?
A collection is a remote root plus discovery rules. On `collection pull`, Biblicus lists subfolders and mirrors
each subfolder into its own corpus under a dedicated local root. Discovery is deterministic, and mirroring is
one-way: remote is authoritative; local content is updated or pruned to match.

Example: Azure Blob container `nexus` with subfolders named by `prospect_id`.

```
nexus/
  catalyst/
  acme/
  globex/
```

Each folder becomes:
```
corpora/nexus/catalyst
corpora/nexus/acme
corpora/nexus/globex
```

### What is a pipeline recipe?
Pipeline recipes are a single YAML file that declare:
- target corpus or collection selector
- extraction recipe
- retrieval configuration
- analysis runs

They serve as an executable, version-controlled “program” for repeatable information pipelines.

### How do credentials work?
Credentials are defined as **source profiles** in user config, not in corpus or collection configs.
This allows multiple accounts and providers at once without embedding secrets in corpora.

### How does this affect existing workflows?
This is a **breaking change by design**. We will provide one official way to configure and run collections and
pipeline recipes. Old workflows that assume a single remote source per corpus must migrate to collections.

### What are the non-goals?
- Two-way synchronization
- Implicit or hidden discovery rules
- Automatic extraction or retrieval without an explicit recipe
- Storing credentials in corpus or collection configs

### FAQs
**Q: Is this “sync”?**  
No. It is a **one-way mirror** from the remote source to local corpora.

**Q: What if a remote folder disappears?**  
The local corpus is archived and excluded from future mirroring. It is not deleted silently.

**Q: Can I map subfolders to tables instead of corpora?**  
Yes. Collections can define partition rules that tag items with table metadata instead of creating corpora.

**Q: Can I target multiple sources at once?**  
Yes. Source profiles allow many remote accounts and providers in parallel.

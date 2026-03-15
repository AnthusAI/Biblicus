# PR-FAQ: Markov LLM Observation Cache

## Press Release

**Biblicus speeds up Markov analysis with automatic LLM observation caching.**

Today we’re introducing automatic, per-item caching for LLM observation labeling in Markov analysis. The first run labels each segment once, stores the results, and every subsequent run reuses them—even if you rerun with a different sample size or restart mid-run. This makes iterative HMM analysis practical without repeatedly paying for the same labels.

The cache is keyed by the LLM client configuration (minus the API key), prompt templates, and an optional cache name. Change any of those inputs and Biblicus automatically creates a fresh cache. The cache lives under the corpus’s `.biblicus/cache` directory and can be deleted safely at any time.

Alongside the cache, Markov analysis now keeps the topic modeling report visible even when observations are reused, so `output.json` stays complete across restarts.

## FAQ

**Why do we need this?**
Markov analysis often requires multiple runs while tuning segmentation, topics, and HMM settings. Without caching, each run re-labels the same segments. The cache makes that work idempotent and repeatable.

**How is the cache keyed?**
The cache id is a hash of `{cache_name, llm client (minus api_key), prompt_template, system_prompt}`. This ensures that a prompt change or model change yields a new cache.

**Where is the cache stored?**
`.biblicus/cache/markov/llm-observations/<cache_id>/<extractor_id>/<snapshot_id>/`

**What happens when I change prompts or models?**
A new `cache_id` is produced, so Biblicus writes to a new cache directory. The previous cache is preserved for reproducibility.

**How do I delete the cache?**
Remove the cache directory for the corpus:
`.biblicus/cache/markov/llm-observations/`

**Does this change my analysis outputs?**
No. The cached labels are the same data that would be generated on demand. The output remains deterministic for the same inputs.

**What if the cache is incomplete?**
Biblicus only generates labels for missing segments and updates the cache incrementally. Partial runs are safe.

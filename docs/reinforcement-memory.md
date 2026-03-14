# Reinforcement Memory

## PR FAQ

### Press Release

Biblicus now includes **Reinforcement Memory** -- a system for discovering and tracking semantic patterns in timestamped text streams. Feed it a series of texts over time and it organizes them into topic clusters, tracks which patterns are growing or fading, labels them with natural language, and infers root causes. It remembers what it has seen before: new texts that match existing patterns reinforce those memories, while patterns that stop appearing gradually decay.

Reinforcement Memory is designed for any domain where you need to understand *what people are repeatedly saying* and *how those themes change over time*. Quality assurance feedback, support tickets, survey responses, user reviews, incident reports -- anywhere a stream of human-written text contains latent recurring themes.

The system is built from composable pieces. Bring your own embedding model, vector store, and LLM -- or use the provided defaults. Data is persisted via Virtuus (JSON files with indexed queries), so the full analysis state lives in a plain folder you can inspect, version-control, or back up.

### FAQ

**Q: What problem does this solve?**

When humans write feedback, complaints, or observations over time, recurring themes emerge -- but they're buried in free text. Reinforcement Memory surfaces those themes automatically, tracks them as living patterns that strengthen or fade, and explains why they exist. Without it, you either read every text manually or run one-shot topic models that can't track change over time.

**Q: What is a "reinforcement memory" conceptually?**

It borrows from how biological memory works. A pattern you encounter once is fragile. A pattern you encounter repeatedly becomes stronger -- reinforced. A pattern you stop encountering fades. Each topic cluster is a memory with a weight between 0.0 and 1.0:

- **Reinforcement**: When new texts match an existing cluster, its weight increases toward 1.0.
- **Decay**: When no new texts match a cluster over time, its weight decreases toward 0.0.
- **Tiers**: Hot (>= 0.7), Warm (>= 0.3), Cold (< 0.3). Cold memories can be pruned.

This makes the system inherently temporal -- it doesn't just tell you *what* the patterns are, but *which ones are active right now* versus *which ones are fading*.

**Q: What does the pipeline look like end-to-end?**

1. **Ingest** -- Timestamped texts arrive (with optional metadata) and are persisted in Virtuus.
2. **Embed** -- Each text is converted to a vector embedding. Results are cached so re-analysis doesn't re-embed.
3. **Cluster** -- Embeddings are clustered via BERTopic (UMAP + HDBSCAN), with KMeans fallback for small datasets.
4. **Characterize** -- Each cluster gets: centroid embedding, p95 distance boundary, TF-IDF keywords, representative exemplars.
5. **Label** -- An LLM generates a concise human-readable label from keywords and exemplars.
6. **Lifecycle** -- Timestamps of cluster members determine lifecycle tier: *new*, *trending*, or *established*.
7. **Reinforce/Decay** -- Clusters that received new texts are reinforced; those that didn't are decayed.
8. **Causal Inference** -- Optionally, an LLM infers a root cause for each cluster from exemplar context.
9. **Persist** -- Cluster centroids go to the vector store (for future similarity queries); topic state goes to Virtuus (for tracking over time).

**Q: What does the API look like?**

```python
from biblicus.analysis.reinforcement_memory import (
    ReinforcementMemory,
    TimestampedText,
    LocalVectorStore,
    sentence_transformer_embedder,
)

memory = ReinforcementMemory(
    data_dir="./my_analysis",
    vector_store=LocalVectorStore("./my_analysis/vectors"),
    embed=sentence_transformer_embedder(),
)

# Ingest texts
memory.ingest([
    TimestampedText(
        id="1",
        group_id="support-tickets",
        timestamp="2024-01-15T10:00:00Z",
        text="The pricing page is confusing",
        metadata={"source": "zendesk", "priority": "high"},
    ),
    # ... more texts
])

# Analyze -- clusters, labels, weights, lifecycle
result = memory.analyze(group_id="support-tickets")

for topic in result.topics:
    print(f"{topic.label} ({topic.memory_tier}, {topic.lifecycle_tier})")
    print(f"  Weight: {topic.memory_weight:.2f}, Members: {topic.member_count}")
    print(f"  Keywords: {', '.join(topic.keywords[:5])}")
    if topic.root_cause:
        print(f"  Cause: {topic.root_cause}")
```

**Q: What is the `group_id` for?**

It partitions texts into independent analysis groups. In a QA system, each question being scored might be a group. In a support system, each product area might be a group. Texts within a group are clustered together; different groups are analyzed independently.

**Q: What are the pluggable components?**

| Component | Type | Provided implementations |
|-----------|------|--------------------------|
| Vector store | `VectorStore` protocol | `LocalVectorStore` (file-backed NumPy), `S3VectorStore` (AWS S3 Vectors) |
| Embedding | `Callable[[list[str]], ndarray]` | `sentence_transformer_embedder()`, `dspy_embedder()`, `hash_embedder()` (tests) |
| Topic labeling | `Callable[[keywords, exemplars], str]` | `dspy_labeler()`, `bedrock_labeler()` |
| Causal inference | `Callable[[text, context], str]` | `dspy_causal()`, `bedrock_causal()` |

All are optional except `embed` and `vector_store`. Without LLM callables, labels fall back to top keywords and causal inference is skipped.

**Q: How does persistence work?**

Virtuus stores all structured state as JSON files in the `data_dir`:

```
my_analysis/
  texts/       # One JSON file per ingested text
  topics/      # One JSON file per discovered topic
  runs/        # One JSON file per analysis run
  vectors/     # Vector store data (if using LocalVectorStore)
```

This is a plain folder. You can `git init` it, rsync it, or inspect individual records with `cat`. Virtuus builds in-memory indexes (GSIs) at load time for fast queries by group and timestamp -- similar to DynamoDB GSIs but over local JSON files.

**Q: What about production use with AWS?**

For production, use `S3VectorStore` backed by AWS S3 Vectors -- a managed vector index service. Biblicus provides a CDK stack (`infrastructure/reinforcement-memory/`) that provisions:

- An S3 Vectors bucket and cosine-similarity index
- An S3 bucket for embedding cache

Deploy it with `cdk deploy` and pass the resource names to `S3VectorStore`. Alternatively, provision these resources yourself (or let your host application provision them, as Plexus does).

**Q: What is the relationship between this and the existing topic modeling backend?**

The existing `topic-modeling` analysis backend (`biblicus analyze topic-modeling`) is a one-shot corpus analysis tool -- it takes a corpus, extracts text, and produces a static topic model. Reinforcement Memory is a different concept: it's a living, evolving analysis system that tracks patterns *over time* with reinforcement and decay. They share the underlying BERTopic clustering primitive but serve different purposes.

**Q: How does lifecycle tracking work?**

Each text in a cluster has a timestamp. The system looks at where those timestamps fall relative to now:

- **Short-term window**: last 14 days
- **Medium-term window**: 15-30 days
- **Long-term**: older than 30 days

From this:
- **New**: Only short-term members. A pattern that just appeared.
- **Trending**: Short-term or medium-term members, but nothing long-term. A pattern that's active and growing.
- **Established**: Has long-term members. A pattern that has persisted.

Combined with the memory weight (hot/warm/cold), this gives a two-dimensional view: a topic can be *established but cold* (was a pattern, has faded) or *new and hot* (just appeared and is being reinforced heavily).

**Q: How does this relate to Plexus?**

Plexus was the first consumer. It uses Reinforcement Memory to analyze feedback edit comments -- when human reviewers correct AI scoring, their written explanations are clustered to reveal systematic issues. Plexus converts its `FeedbackItem` records to `TimestampedText`, provides its own S3 vector store bucket, and maps the `AnalysisResult` back into its report format. The core analysis engine lives in Biblicus; the domain-specific wiring lives in Plexus.

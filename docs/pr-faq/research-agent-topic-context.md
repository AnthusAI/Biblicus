# Research Agent Topic Context PR-FAQ

## Press Release

Biblicus can now generate a compact Markdown topic context report for research agents. The report reads a reproducible topic-modeling snapshot, ranks the most useful topic buckets, and includes representative examples with titles, subtitles, abstracts, or summaries so an agent can understand what is already in the knowledge base before looking for new material.

## FAQ

### Who is this for?

This report is for research agents that need orientation before expanding a corpus. It gives the agent a concise map of existing topic coverage without turning discovered topics into reviewed canonical taxonomy changes.

### What does the report contain?

Each report includes up to 20 non-outlier topic buckets by default. Each topic includes the BERTopic label, topic identifier, document count, keywords, optional LLM-generated guidance, and up to three representative examples.

### How are examples selected?

Examples are selected deterministically from the topic's assigned documents. Biblicus scores each document by term-vector similarity to the other documents in the same topic and chooses the most central examples first. This avoids random examples and gives the research agent documents that are typical of the bucket.

### What text is shown for examples?

Biblicus prefers curated metadata: title, subtitle, and abstract. If no abstract exists, it uses an existing summary or description. If a summary model is configured, Biblicus can summarize extracted text for examples that lack abstract-like metadata.

### Does this require an LLM?

No. The command can run without an LLM and still produce topic labels, keywords, and representative examples from the existing snapshot. Passing `--summary-model` enables OpenAI-generated topic guidance and missing-example summaries.

### Does this mutate the classifier or seed manifests?

No. The report is context only. It does not promote predictions, edit seed manifests, or accept governance proposals.

### Why is this tied to a topic-modeling snapshot?

The research context must be reproducible. A topic-modeling snapshot fixes the corpus catalog, extraction snapshot, topic assignments, labels, and document membership used by the report.

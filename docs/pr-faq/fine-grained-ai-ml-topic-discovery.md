# Fine-Grained AI-ML Topic Discovery PR-FAQ

## Press Release

Biblicus now has a repeatable workflow for fine-grained AI/ML topic discovery. Instead of clustering full article text, the AI-ML-Research corpus can model compact title and abstract metadata, sweep several granularity profiles, and label the winning BERTopic model with BERTopic representation models backed by OpenAI.

## FAQ

### Why use titles and abstracts for topic discovery?

Full text is still the right source for retrieval and evidence, but first-pass topic discovery needs a compact description of what the paper is about. Titles and abstracts reduce boilerplate, references, author lists, and article chrome that cause small corpora to collapse into broad clusters.

### How are topic labels generated?

Topic labels come from BERTopic representation models. Biblicus passes the configured representation model into `BERTopic(representation_model=...)` so BERTopic owns the label refinement step. Biblicus no longer treats a separate post-processing LLM labeling stage as the official topic-modeling path.

### How does the granularity sweep work?

The sweep runs three built-in profiles: `coarse`, `balanced`, and `fine`. It runs them without representation labels first, ranks them against the target topic-count range, chooses the best profile, and then reruns the selected profile with the configured BERTopic representation model.

### What target should AI-ML-Research use?

The initial target is 10 to 20 non-outlier topics. That is intentionally a tuning target, not a guarantee. When the corpus is still small, Biblicus reports the closest profile and shows the largest topic share so curators can see whether the result is still too coarse.

### Do candidate labels leak into discovery?

No. The official AI-ML topic input recipe uses `title` and `metadata.abstract` only. Tags, curation fields, proposed topic identifiers, and seed manifests are excluded from unsupervised discovery.

### What is not included?

This does not change the reviewed topic classifier manifest, does not promote discovered clusters into canonical topics, and does not use a custom Biblicus LLM labeling loop for topic names.

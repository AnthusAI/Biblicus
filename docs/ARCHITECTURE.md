# Biblicus Architecture

Biblicus sits between raw, unstructured data and the moment you need reliable answers from it.
It is built for teams who receive large, messy corpora and must extract usable signals without
losing provenance or reproducibility. Retrieval-augmented generation is one use case, but the
system is broader than chatbots: it supports any pipeline that needs structured insight from
unstructured data.

At a high level the system does five things:

1. **Ingests** raw content into a corpus with minimal friction.
2. **Extracts** text from diverse media (documents, images, audio).
3. **Transforms** and annotates text with reusable LLM utilities.
4. **Retrieves** evidence through explicit, reproducible stages.
5. **Evaluates** results so improvements are measurable, not anecdotal.

The guiding idea is that every retrieval produces **evidence**: structured outputs with scores
and provenance that can be inspected, audited, and reused. Context packs, summaries, and downstream
generation are all derived from that evidence.

## Why it exists

Real-world AI work often starts with a folder full of files, not a clean database. Biblicus is the
toolkit that turns those files into a manageable, testable system. It supports workflows like:

- Indexing large collections of emails and making them searchable while protecting sensitive data.
- Processing discovery dumps of scanned PDFs with OCR and extracting evidence for analysis.
- Turning policy or rules documents into a controlled knowledge base for assistants.

## How it fits into AI systems

Biblicus integrates with agent frameworks through explicit tool interfaces. It does not hide
retrieval inside the model. Instead, it provides repeatable pipelines that expose *what* was
retrieved and *why*, so models can use evidence directly and safely.

## Where to go next

- Start with **CORPUS** and **EXTRACTION** to understand how raw content is ingested.
- Move to **RETRIEVAL** and **RETRIEVAL_EVALUATION** to see how evidence is produced and tested.
- Explore **TOPIC_MODELING** and **MARKOV_ANALYSIS** if you need higher-level analysis tools.
- See **TEXT_UTILITIES** for reusable, AI-assisted text transformations.

## Detailed architecture and policies

For a deep, internal reference (including design policies and architectural constraints), see
`ARCHITECTURE_DETAIL.md`.

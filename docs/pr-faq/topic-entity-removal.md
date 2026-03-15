# PR-FAQ: Entity Removal Preprocessing for Topic Modeling (Draft)

## Press Release

Today we are introducing a local, non-LLM entity removal stage for Biblicus topic modeling. The new stage removes named entities (for example, people, locations, organizations, dates, and identifiers) before BERTopic runs so that topical buckets reflect intent rather than proper nouns or IDs. This reduces topic fragmentation, improves bucket cohesion, and keeps topic labels focused on intent rather than specific values.

The feature is fully optional and configurable. It uses a local NLP model (spaCy) and does not require any external services or LLM calls. When enabled, entity removal happens after optional text extraction but before lexical processing and BERTopic, preserving the rest of the pipeline.

## FAQ

**Why add entity removal?**
Proper nouns and identifiers (names, addresses, policy numbers) create artificial topic variation. Removing them yields cleaner topic clusters that better reflect the underlying intent (for example, “address verification” instead of many unique addresses).

**Is this LLM-based?**
No. It is local and deterministic using spaCy’s named entity recognition.

**Where does it run in the pipeline?**
Topic modeling pipeline order:
1) Optional LLM extraction (summarization/itemization)
2) Entity removal (new)
3) Lexical processing (lowercase, punctuation, whitespace)
4) BERTopic
5) Optional LLM topic labeling (fine-tuning)

**How is it configured?**
A new optional config block is proposed for topic modeling preprocessing, for example:

```
entity_removal:
  enabled: true
  provider: spacy
  model: en_core_web_sm
  entity_types: [PERSON, GPE, LOC, ORG, FAC, DATE, TIME, MONEY, PERCENT, CARDINAL, ORDINAL]
  replace_with: ""
  collapse_whitespace: true
```

**Can I remove emails, phone numbers, or policy IDs?**
Yes. We will support optional regex-based removals alongside NER for structured identifiers. This will be configurable and applied after NER.

**Will this change existing snapshots?**
Only when enabled. The preprocessing config becomes part of the topic modeling configuration, so snapshot identities remain reproducible and deterministic.

**What happens if spaCy isn’t installed?**
If enabled and unavailable, the run fails with a clear error recommending `pip install "biblicus[ner]"` (exact extra to be finalized).

**Is this only for topic modeling?**
Initial integration is for topic modeling, but the utility is designed to be reusable for other text pipelines.

**Will this redact sensitive data?**
It removes entity spans entirely (or replaces with a configured token). It is not a full redaction system and is not a compliance feature.

**How does this relate to LLM topic labeling?**
Entity removal reduces noise before BERTopic. LLM topic labeling then uses keywords and exemplars from the cleaned topics, producing more stable labels.

**How do I disable it?**
Set `entity_removal.enabled: false` (default).

**Does it slow things down?**
It adds a local NLP pass but replaces far more expensive LLM summarization in many workflows. Overall, it should reduce cost and improve throughput.

**How do we test it?**
BDD specs will validate that entity removal reduces topic fragmentation and that removal is deterministic given the same input.

# Entity removal

Entity removal is a local, non-LLM preprocessing step that deletes named entities from text before downstream
analysis. It is designed to reduce topic fragmentation caused by proper nouns and identifiers (for example, names,
addresses, policy numbers).

This utility is optional and deterministic. It relies on a local spaCy model and does not send text to external
services.

## When to use it

Use entity removal when you want topic modeling or clustering to focus on intent rather than unique values.
Common examples include:

- Removing addresses, policy numbers, and names in customer-service transcripts.
- Collapsing location-specific variants into a single intent bucket.
- Cleaning entity-heavy corpora where proper nouns dominate keywords.

## Installation

Entity removal uses spaCy. Install the optional dependency and the model:

```
pip install "biblicus[ner]"
python -m spacy download en_core_web_sm
```

## Configuration

Entity removal is configured under topic modeling and runs after LLM extraction (if enabled) and before lexical
processing.

```yaml
entity_removal:
  enabled: true
  provider: spacy
  model: en_core_web_sm
  entity_types:
    - PERSON
    - GPE
    - LOC
    - ORG
    - FAC
    - DATE
    - TIME
    - MONEY
    - PERCENT
    - CARDINAL
    - ORDINAL
  replace_with: ""
  collapse_whitespace: true
  regex_patterns:
    - "\\b\\d{5}(-\\d{4})?\\b"  # zip codes
    - "\\b\\d{3}[-. ]?\\d{3}[-. ]?\\d{4}\\b"  # phone numbers
  regex_replace_with: ""
```

### Notes

- When `entity_types` is empty, Biblicus uses a default set of common entity labels.
- Regex patterns run **after** NER removal.
- If `replace_with` is empty, entities are deleted.

## Output visibility

Topic modeling reports include an `entity_removal` report entry showing:

- provider and model used
- entity types removed
- input/output document counts
- regex patterns applied

When enabled, Biblicus writes `entity_removal.jsonl` alongside the topic modeling `output.json` file. This artifact
contains the redacted documents used for clustering and is reused when rerunning the same snapshot.

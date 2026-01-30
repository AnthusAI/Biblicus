# Context packs

A context pack is the text that your application sends to a large language model.

Biblicus keeps two things separate:

- Retrieval returns **evidence** as structured objects with provenance.
- Context pack building turns evidence into **context pack text** using an explicit policy.

This separation makes retrieval repeatable and testable, while keeping context formatting as an explicit surface you can change, compare, and evaluate.

## Minimal policy

The minimal policy is: join evidence text blocks with a separator.

In Python:

```python
from biblicus.context import ContextPackPolicy, build_context_pack

policy = ContextPackPolicy(join_with="\n\n")
context_pack = build_context_pack(result, policy=policy)
print(context_pack.text)
```

## Policy surfaces

Context pack policies make ordering and formatting explicit.

### Ordering

Use `ordering` to control how evidence blocks are arranged before joining:

- `rank`: use the evidence rank as provided by retrieval.
- `score`: sort by score (descending) and then item identifier.
- `source`: group by source uniform resource identifier, then sort by score.

### Metadata inclusion

Set `include_metadata=True` to prepend metadata to each block. Metadata includes:

- `item_id`
- `source_uri`
- `score`
- `stage`

### Character budgets

Character budgets drop trailing blocks until the context pack fits the specified limit. This keeps context shaping
deterministic without relying on a tokenizer.

In Python:

```python
from biblicus.context import CharacterBudget, ContextPackPolicy, fit_context_pack_to_character_budget

policy = ContextPackPolicy(join_with="\n\n", ordering="score", include_metadata=True)
fitted = fit_context_pack_to_character_budget(context_pack, policy=policy, character_budget=CharacterBudget(max_characters=500))
print(fitted.text)
```

## Command-line interface

The command-line interface can build a context pack from a retrieval result by reading JavaScript Object Notation from standard input.

```bash
biblicus query --corpus corpora/example --query "primary button style preference" \\
  | biblicus context-pack build --ordering score --include-metadata --max-characters 500
```

## What context pack building does

- Includes only usable text evidence.
- Excludes evidence with no text payload or whitespace-only text.

## Token budgets

Fitting context to a token budget is a separate concern. Token counting depends on a specific tokenizer and may vary by model.

Biblicus treats token budgeting as a separate stage so it can be configured, tested, and evaluated independently from retrieval and text formatting.

In Python:

```python
from biblicus.context import (
    ContextPackPolicy,
    TokenBudget,
    fit_context_pack_to_token_budget,
)

fitted_context_pack = fit_context_pack_to_token_budget(
    context_pack,
    policy=policy,
    token_budget=TokenBudget(max_tokens=500),
)
print(fitted_context_pack.text)
```

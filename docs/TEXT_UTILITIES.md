# Text utilities

Biblicus text utilities are small, repeatable building blocks that transform text using a **virtual file editor** pattern.
They are designed for ETL-style pipelines where you need reliable structure without forcing a model to re-emit the entire
document.

This page explains the common mechanism, the human-facing menu of utilities, and how the internal patterns map to those
utilities.

## The virtual file editor pattern

Text utilities work by treating the input text as an in-memory file. The model receives that text plus a strict system
prompt and then edits the file using tool calls:

- `str_replace(old_str, new_str)`
- `view()`
- `done()`

The model does **not** re-emit the whole document. It only inserts markup into the existing text. Biblicus validates the
edits and parses the marked-up text into structured output.

This gives you:

- Lower cost and faster execution on long documents.
- Deterministic validation (no hidden edits).
- Clear failure modes when the model misbehaves.

### Mechanism example

Start with a system prompt that explains the edit protocol and embeds the current text:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
We run fast.
---
```

Then the user prompt focuses only on what to return:

```
USER PROMPT:
Return all the verbs.
```

The input text is the same content shown in the system prompt:

```
INPUT TEXT:
We run fast.
```

The model edits the virtual file by inserting tags in-place:

```
MARKED-UP TEXT:
We <span>run</span> fast.
```

Biblicus returns structured data parsed from the markup:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "We <span>run</span> fast.",
  "spans": [
    {"index": 1, "start_char": 3, "end_char": 6, "text": "run"}
  ],
  "warnings": []
}
```

## Prompt contract

The prompt contract is intentionally simple and split across two messages:

- **System**: explains the editing protocol and the exact markup rules.
- **User**: describes *what to return* (for example, “Return all verbs.”).

This keeps small models focused. They only need to understand one job at a time while the system message handles the
editing mechanics.

## Human-facing utilities

The human menu is **outcome-oriented**. Each utility has a simple prompt contract, so small models only need to focus on
one job at a time.

- **Extract**: return spans that match a request.
  - Example: "Return the quoted payment statement."
- **Slice**: return ordered segments.
  - Example: "Return each sentence as a slice."
- **Annotate**: return spans with attributes when labels are required.
  - Example: "Return all the verbs."
- **Redact**: return spans to remove or mask.
  - Example: "Return all email addresses."
- **Link**: return spans connected by id/ref relationships.
  - Example: "Return repeated mentions of the same company and link repeats to the first mention."

These utilities are intentionally simple at the prompt layer, even though they share the same internal tool loop.

## Internal patterns

Internally, Biblicus uses a small number of repeatable interaction patterns and maps the human-facing utilities to them.
The user does not need to know these details, but they explain why the system is consistent across tasks.

- **Span insertion**: inserts `<span>...</span>` around requested text.
- **Slice markers**: inserts `<slice/>` to split the text into ordered segments.
- **Attributed spans**: inserts `<span phase="...">...</span>` when labels are required.
- **Linked spans**: inserts `<span id="...">...</span>` and `<span ref="...">...</span>` pairs.

The system chooses the pattern based on the requested utility. This keeps user prompts simple while preserving a uniform
implementation.

## Choosing the right utility

- Use **extract** when you only need the text itself.
- Use **slice** when ordering matters (phases, steps, turns).
- Use **annotate** only when you must attach attributes or labels.
- Use **redact** when you need to mask or remove sensitive content.
- Use **link** when you need to connect repeated mentions.

## Where to go next

- `docs/TEXT_EXTRACT.md` for span-based extraction.
- `docs/TEXT_SLICE.md` for slice-based segmentation.
- `docs/TEXT_ANNOTATE.md` for attribute-based spans.
- `docs/TEXT_REDACT.md` for redaction spans.
- `docs/TEXT_LINK.md` for id/ref linking.
- `features/text_extract.feature`, `features/text_slice.feature`, and `features/text_utilities.feature` for behavior specs.
- `features/integration_text_extract.feature`, `features/integration_text_slice.feature`,
  `features/integration_text_annotate.feature`, `features/integration_text_redact.feature`, and
  `features/integration_text_link.feature` for live demos.

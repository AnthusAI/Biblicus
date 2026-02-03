# Text annotate

Text annotate is a reusable utility for attaching structured attributes (labels, phases, roles) to spans of text without re-emitting the document.

If you ask a model to "return all the verbs with their types" as a JSON list, you pay for the output tokens of every word, and you risk the model hallucinating words that aren't there.

Text annotate uses the **virtual file pattern** to solve this. Biblicus gives the model a virtual file and asks it to insert XML tags with attributes in-place (e.g., `<span label="verb">...</span>`). The model returns a small edit script (`str_replace` only), and Biblicus applies it and parses the result into structured, attributed spans. You get rich metadata without the cost or risk of text regeneration.

## How text annotate works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only span tags were inserted.
4) The marked-up string is parsed into ordered **spans with attributes**.

The model never re-emits the full text. It only inserts tags in-place.

### Mechanism example

Biblicus supplies an internal protocol that defines the edit protocol, allowed attributes, and embeds the current text:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span ATTRIBUTE="VALUE">...</span> in-place in the current text.
Each span must include exactly one attribute. Allowed attributes: label, phase, role.
Current text:
---
We run fast.
---
```

Then provide a short user prompt describing what to return:

**User prompt:**

```
Return all the verbs.
```

The input text is the same content embedded in the internal protocol:

**Input text:**

```
We run fast.
```

The model edits the virtual file by inserting tags in-place:

**Marked-up text:**

```
We <span label="verb">run</span> fast.
```

Biblicus returns structured data parsed from the markup:

**Structured data (result):**

```
{
  "marked_up_text": "We <span label=\"verb\">run</span> fast.",
  "spans": [
    {
      "index": 1,
      "start_char": 3,
      "end_char": 6,
      "text": "run",
      "attributes": {"label": "verb"}
    }
  ],
  "warnings": []
}
```

## Data model

Text annotate uses Pydantic models for strict validation:

- `TextAnnotateRequest`: input text + LLM config + prompt template + allowed attributes.
- `TextAnnotateResult`: marked-up text and attributed spans.

Internal protocol templates (advanced overrides) must include `{text}`. Prompt templates must not include `{text}` and
should only describe what to return. The internal protocol template can interpolate the allowed attributes list via
Jinja2.

Most callers only supply the user prompt and text. Override `system_prompt` only when you need to customize the edit
protocol.

## Output contract

Text annotate is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="Hello", new_str="<span label=\"greeting\">Hello</span>")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with span tags inserted.
- Only `<span ...>` and `</span>` tags are allowed.
- Each span must include exactly one attribute.
- Attributes must be on the allow list.

Long-span handling: the system prompt instructs the model to insert `<span>` and `</span>` in separate `str_replace` calls for long passages (single-call insertion is allowed for short spans). This is covered by unit tests in `tests/test_text_utility_tool_calls.py`.

## Example: Python API

```python
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextAnnotateRequest, apply_text_annotate

request = TextAnnotateRequest(
    text="We run fast.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    prompt_template="Return all the verbs.",
    allowed_attributes=["label", "phase", "role"],
)
result = apply_text_annotate(request)
```

## Concept: Text Annotate FAQ

### What problem does this solve?

Some ETL pipelines need **labeled spans**, not just extracted spans. For example, you may want phases of a conversation (greeting, verification, resolution) or roles (agent vs customer). Existing extract/slice utilities can return spans, but they cannot attach structured attributes in a consistent way. Text annotate provides a standardized way to attach attributes while preserving the original text.

### How is it different from text extract?

- **Extract** returns spans only (no attributes).
- **Annotate** returns spans with attributes (when labels are required).

This keeps prompts simple for small models by using annotate only when needed.

### Why not just use JSON output?

The virtual file editor pattern avoids re-emitting the full document, which reduces token cost and improves reliability on long texts. It also allows deterministic validation of the original text.

### Is this a replacement for NER or classification models?

No. It is a **text utility** for structured annotation within a single document. It’s designed for ETL pipelines that need deterministic output and traceability, not generalized model training.

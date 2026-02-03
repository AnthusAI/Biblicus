# Text redact

Text redact is a reusable utility for identifying sensitive spans in text without re-emitting the document.

If you ask a model to "rewrite this document with PII removed," you risk the model leaking information it was supposed to remove, or hallucinating new text during the rewrite. The cost of regenerating the full document is also high.

Text redact uses the **virtual file pattern** to ensure safety and efficiency. Biblicus gives the model a virtual file and asks it to wrap sensitive spans in XML tags (e.g., `<span redact="pii">...</span>`). The model returns a small edit script (`str_replace` only), and Biblicus applies it. This allows you to identify exactly what to remove without ever asking the model to generate the "clean" text itself.

## How text redact works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only span tags were inserted.
4) The marked-up string is parsed into ordered **redaction spans**.

### Mechanism example

Biblicus supplies an internal protocol that defines the edit protocol and embeds the current text:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Do not add any span attributes.
Current text:
---
Contact us at demo@example.com for help.
---
```

Then provide a short user prompt describing what to return:

**User prompt:**

```
Return all email addresses.
```

The input text is the same content embedded in the internal protocol:

**Input text:**

```
Contact us at demo@example.com for help.
```

The model edits the virtual file by inserting tags in-place:

**Marked-up text:**

```
Contact us at <span>demo@example.com</span> for help.
```

Biblicus returns structured data parsed from the markup:

**Structured data (result):**

```
{
  "marked_up_text": "Contact us at <span>demo@example.com</span> for help.",
  "spans": [
    {
      "index": 1,
      "start_char": 14,
      "end_char": 30,
      "text": "demo@example.com",
      "attributes": {}
    }
  ],
  "warnings": []
}
```

### Redaction types example

You can enable redaction types by allowing a `redact` attribute in the internal protocol:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Each span must include a redact attribute with one of: pii.
Current text:
---
Account 1234 should be removed.
---
```

User prompt:

**User prompt:**

```
Return the account identifiers.
```

Input text:

**Input text:**

```
Account 1234 should be removed.
```

Marked-up text:

**Marked-up text:**

```
<span redact="pii">Account 1234</span> should be removed.
```

Structured data:

**Structured data (result):**

```
{
  "marked_up_text": "<span redact=\"pii\">Account 1234</span> should be removed.",
  "spans": [
    {
      "index": 1,
      "start_char": 0,
      "end_char": 12,
      "text": "Account 1234",
      "attributes": {"redact": "pii"}
    }
  ],
  "warnings": []
}
```

## Data model

Text redact uses Pydantic models for strict validation:

- `TextRedactRequest`: input text + LLM config + prompt template + optional redaction types.
- `TextRedactResult`: marked-up text and redaction spans.

Internal protocol templates (advanced overrides) must include `{text}`. Prompt templates must not include `{text}` and
should only describe what to return. The internal protocol template can interpolate redaction types via Jinja2.

Most callers only supply the user prompt and text. Override `system_prompt` only when you need to customize the edit
protocol.

## Output contract

Text redact is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="demo@example.com", new_str="<span>demo@example.com</span>")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with span tags inserted.
- When redaction types are enabled, use `redact="TYPE"`.
- When redaction types are disabled, do not include span attributes.

Long-span handling: the system prompt instructs the model to insert `<span>` and `</span>` in separate `str_replace` calls for long passages (single-call insertion is allowed for short spans). This is covered by unit tests in `tests/test_text_utility_tool_calls.py`.

## Example: Python API

```python
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextRedactRequest, apply_text_redact

request = TextRedactRequest(
    text="Account 1234 should be removed.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    prompt_template="Return the account identifiers.",
    redaction_types=["pii"],
)
result = apply_text_redact(request)
```

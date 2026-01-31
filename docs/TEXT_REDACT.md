# Text redact

Text redact is a reusable utility for marking sensitive spans in text with XML tags. It uses the virtual file editor
pattern and returns structured spans, without forcing the model to re-emit the entire document.

## How text redact works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only span tags were inserted.
4) The marked-up string is parsed into ordered **redaction spans**.

### Mechanism example

Start with a system prompt that defines the edit protocol and embeds the current text:

```
SYSTEM PROMPT (excerpt):
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

```
USER PROMPT:
Return all email addresses.
```

The input text is the same content embedded in the system prompt:

```
INPUT TEXT:
Contact us at demo@example.com for help.
```

The model edits the virtual file by inserting tags in-place:

```
MARKED-UP TEXT:
Contact us at <span>demo@example.com</span> for help.
```

Biblicus returns structured data parsed from the markup:

```
STRUCTURED DATA (result):
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

You can enable redaction types by allowing a `redact` attribute in the system prompt:

```
SYSTEM PROMPT (excerpt):
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

```
USER PROMPT:
Return the account identifiers.
```

Input text:

```
INPUT TEXT:
Account 1234 should be removed.
```

Marked-up text:

```
MARKED-UP TEXT:
<span redact="pii">Account 1234</span> should be removed.
```

Structured data:

```
STRUCTURED DATA (result):
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

System prompts must include `{text}`. Prompt templates must not include `{text}` and should only describe what to
return. The system prompt template can interpolate redaction types via Jinja2.

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

## Example: Python API

```
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextRedactRequest, apply_text_redact

system_prompt = """
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
{% if redaction_types %}
Each span must include a redact attribute with one of: {{ redaction_types | join(', ') }}.
{% else %}
Do not add any span attributes.
{% endif %}

Use the str_replace tool to insert span tags and the done tool when finished.
When finished, call done. Do NOT return JSON in the assistant message.

Rules:
- Use str_replace only.
- old_str must match exactly once in the current text.
- old_str and new_str must be non-empty strings.
- new_str must be identical to old_str with only <span ...> and </span> inserted.
- Do not include <span or </span> inside old_str or new_str.
- Do not insert nested spans.
- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.
- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.
- Do not delete, reorder, or paraphrase text.

Current text:
---
{text}
---
""".strip()

request = TextRedactRequest(
    text="Account 1234 should be removed.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    system_prompt=system_prompt,
    prompt_template="Return the account identifiers.",
    redaction_types=["pii"],
)
result = apply_text_redact(request)
```

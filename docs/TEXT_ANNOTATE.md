# Text annotate

Text annotate is a reusable utility for extracting spans **with attributes** using a language model. It uses the same
virtual file editor pattern as text extract, but each span carries exactly one attribute so downstream tools can reason
about labels and categories.

## How text annotate works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only span tags were inserted.
4) The marked-up string is parsed into ordered **spans with attributes**.

The model never re-emits the full text. It only inserts tags in-place.

### Mechanism example

Biblicus supplies an internal protocol that defines the edit protocol, allowed attributes, and embeds the current text:

```
INTERNAL PROTOCOL (excerpt):
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

```
USER PROMPT:
Return all the verbs.
```

The input text is the same content embedded in the internal protocol:

```
INPUT TEXT:
We run fast.
```

The model edits the virtual file by inserting tags in-place:

```
MARKED-UP TEXT:
We <span label="verb">run</span> fast.
```

Biblicus returns structured data parsed from the markup:

```
STRUCTURED DATA (result):
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

## Example: Python API

```
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

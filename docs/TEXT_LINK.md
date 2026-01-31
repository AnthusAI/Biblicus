# Text link

Text link is a reusable utility for connecting repeated mentions with id/ref spans. It uses the virtual file editor
pattern and returns structured spans without re-emitting the full text.

## How text link works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates id/ref rules.
4) The marked-up string is parsed into ordered **linked spans**.

### Mechanism example

Start with a system prompt that defines the edit protocol and embeds the current text:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span ATTRIBUTE="VALUE">...</span> in-place in the current text.
Each span must include exactly one attribute: id for first mentions and ref for repeats.
Id values must start with "link_".
Current text:
---
Acme launched a product. Later, Acme reported results.
---
```

Then provide a short user prompt describing what to return:

```
USER PROMPT:
Return repeated mentions of the same company and link repeats to the first mention.
```

The input text is the same content embedded in the system prompt:

```
INPUT TEXT:
Acme launched a product. Later, Acme reported results.
```

The model edits the virtual file by inserting tags in-place:

```
MARKED-UP TEXT:
<span id="link_1">Acme launched a product</span>. Later, <span ref="link_1">Acme reported results</span>.
```

Biblicus returns structured data parsed from the markup:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span id=\"link_1\">Acme launched a product</span>. Later, <span ref=\"link_1\">Acme reported results</span>.",
  "spans": [
    {
      "index": 1,
      "start_char": 0,
      "end_char": 25,
      "text": "Acme launched a product",
      "attributes": {"id": "link_1"}
    },
    {
      "index": 2,
      "start_char": 33,
      "end_char": 53,
      "text": "Acme reported results",
      "attributes": {"ref": "link_1"}
    }
  ],
  "warnings": []
}
```

## Data model

Text link uses Pydantic models for strict validation:

- `TextLinkRequest`: input text + LLM config + prompt template + id prefix.
- `TextLinkResult`: marked-up text and linked spans.

System prompts must include `{text}`. Prompt templates must not include `{text}` and should only describe what to
return. The system prompt template can interpolate the id prefix via Jinja2.

## Output contract

Text link is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="Acme launched a product", new_str="<span id=\"link_1\">Acme launched a product</span>")
str_replace(old_str="Acme reported results", new_str="<span ref=\"link_1\">Acme reported results</span>")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with span tags inserted.
- Use id for first mentions and ref for repeats.
- Id values must start with the configured prefix.

## Example: Python API

```
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextLinkRequest, apply_text_link

system_prompt = """
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span ATTRIBUTE=\"VALUE\">...</span> in-place in the current text.
Each span must include exactly one attribute: id for first mentions and ref for repeats.
Id values must start with "{{ id_prefix }}".

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

request = TextLinkRequest(
    text="Acme launched a product. Later, Acme reported results.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    system_prompt=system_prompt,
    prompt_template="Return repeated mentions of the same company and link repeats to the first mention.",
    id_prefix="link_",
)
result = apply_text_link(request)
```

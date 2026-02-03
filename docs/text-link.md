# Text link

Text link is a reusable utility for connecting repeated mentions (coreference resolution) without re-emitting the text.

If you ask a model to "return a list of all entity mentions and their canonical IDs," you face the same hallucination and cost issues as other extraction tasks.

Text link uses the **virtual file pattern** to handle this in-place. Biblicus asks the model to wrap mentions in XML tags with ID/REF attributes (e.g., `<span id="link_1">...</span>` and `<span ref="link_1">...</span>`). The model returns a small edit script, and Biblicus parses it into a graph of connected spans. This lets you resolve entities and structure relationships without regenerating the content.

## How text link works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates id/ref rules.
4) The marked-up string is parsed into ordered **linked spans**.

### Mechanism example

Biblicus supplies an internal protocol that defines the edit protocol and embeds the current text:

**Internal protocol (excerpt):**

```
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

**User prompt:**

```
Link repeated mentions of the same company to the first mention.
```

The input text is the same content embedded in the internal protocol:

**Input text:**

```
Acme launched a product. Later, Acme reported results.
```

The model edits the virtual file by inserting tags in-place:

**Marked-up text:**

```
<span id="link_1">Acme launched a product</span>. Later, <span ref="link_1">Acme reported results</span>.
```

Biblicus returns structured data parsed from the markup:

**Structured data (result):**

```
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

Internal protocol templates (advanced overrides) must include `{text}`. Prompt templates must not include `{text}` and
should only describe what to return. The internal protocol template can interpolate the id prefix via Jinja2.

Most callers only supply the user prompt and text. Override `system_prompt` only when you need to customize the edit
protocol.

## Output contract

Text link is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="Acme launched a product", new_str="<span id=\"link_1\">Acme</span> launched a product")
str_replace(old_str="Acme reported results", new_str="<span ref=\"link_1\">Acme</span> reported results")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with span tags inserted.
- Use id for first mentions and ref for repeats.
- Id values must start with the configured prefix.
- Id/ref spans must wrap the same repeated text (avoid wrapping extra words).

Long-span handling: the system prompt instructs the model to insert `<span>` and `</span>` in separate `str_replace` calls for long passages (single-call insertion is allowed for short spans). This is covered by unit tests in `tests/test_text_utility_tool_calls.py`.

## Example: Python API

```python
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextLinkRequest, apply_text_link

request = TextLinkRequest(
    text="Acme launched a product. Later, Acme reported results.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    prompt_template="Link repeated mentions of the same company to the first mention.",
    id_prefix="link_",
)
result = apply_text_link(request)
```

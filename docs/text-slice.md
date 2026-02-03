# Text slice

Text slice is a reusable utility for cutting long texts into ordered slices with a language model without requiring the
model to re-emit the full content.

If you ask a model to "split this text into sections" and return the text of each section, you double your token costs and wait for the generation of content you already have.

Text slice uses the **virtual file pattern** to avoid this. Biblicus gives the model a virtual file and asks it to insert `<slice/>` markers in-place. The model returns a small edit script (`str_replace` only), and Biblicus applies it and parses the result into slices. You get perfect boundary detection without paying for the content tokens.

## How text slice works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only `<slice/>` markers were inserted.
4) The marked-up string is split into ordered **slices**.

The model never re-emits the full text, which lowers cost and reduces timeouts on long documents.

### Mechanism example

Biblicus supplies an internal protocol that defines the edit protocol and embeds the current text:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: insert <slice/> markers
at the boundaries of the returned slices in the current text.
Current text:
---
One. Two.
---
```

Then provide a short user prompt describing what to return:

**User prompt:**

```
Return each sentence as a slice.
```

The input text is the same content embedded in the internal protocol:

**Input text:**

```
One. Two.
```

The model edits the virtual file by inserting markers in-place:

**Marked-up text:**

```
One.<slice/> Two.
```

Biblicus returns structured data parsed from the markup:

**Structured data (result):**

```
{
  "marked_up_text": "One.<slice/> Two.",
  "slices": [
    {"index": 1, "start_char": 0, "end_char": 4, "text": "One."},
    {"index": 2, "start_char": 4, "end_char": 9, "text": " Two."}
  ],
  "warnings": []
}
```

## Data model

Text slice uses Pydantic models for strict validation:

- `TextSliceRequest`: input text + LLM config + prompt template.
- `TextSliceResult`: marked-up text and extracted slices.

Internal protocol templates (advanced overrides) must include `{text}`. Both internal protocols and prompt templates
support `{text_length}` placeholders (plus `{error}` for retry hints). Prompt templates must not include `{text}` and
should only describe what to return.

Most callers only supply the user prompt and text. Override `system_prompt` only when you need to customize the edit
protocol.

## Output contract

Text slice is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="Hello world", new_str="Hello<slice/>world")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with only `<slice/>` inserted.
- No modification of the original text.

## Example: Python API

```
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextSliceRequest, apply_text_slice

request = TextSliceRequest(
    text="One. Two. Three.",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    prompt_template="Return each sentence as a slice.",
)
result = apply_text_slice(request)
```

Example snippet:

Internal protocol excerpt:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: insert <slice/> markers
at the boundaries of the returned slices in the current text.
Current text:
---
One. Two. Three.
---
```

User prompt:

**User prompt:**

```
Return each sentence as a slice.
```

Input text:

**Input text:**

```
One. Two. Three.
```

Marked-up text:

**Marked-up text:**

```
One.<slice/> Two.<slice/> Three.
```

Structured data:

**Structured data (result):**

```
{
  "marked_up_text": "One.<slice/> Two.<slice/> Three.",
  "slices": [
    {"index": 1, "start_char": 0, "end_char": 4, "text": "One."},
    {"index": 2, "start_char": 4, "end_char": 9, "text": " Two."},
    {"index": 3, "start_char": 9, "end_char": 16, "text": " Three."}
  ],
  "warnings": []
}
```

## Integration examples

These examples mirror the integration tests and show the minimal user prompts that drive the tool loop.

### Slice sentences

Input text:

```
First one. Second one. Third one.
```

User prompt:

```
Return each sentence as a slice.
```

Expected behavior: `<slice/>` markers are inserted between sentences, producing ordered slices.

Example snippet:

Internal protocol excerpt:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: insert <slice/> markers
at the boundaries of the returned slices in the current text.
Current text:
---
First one. Second one. Third one.
---
```

User prompt:

**User prompt:**

```
Return each sentence as a slice.
```

Input text:

**Input text:**

```
First one. Second one. Third one.
```

Marked-up text:

**Marked-up text:**

```
First one.<slice/> Second one.<slice/> Third one.
```

Structured data:

**Structured data (result):**

```
{
  "marked_up_text": "First one.<slice/> Second one.<slice/> Third one.",
  "slices": [
    {"index": 1, "start_char": 0, "end_char": 10, "text": "First one."},
    {"index": 2, "start_char": 10, "end_char": 22, "text": " Second one."},
    {"index": 3, "start_char": 22, "end_char": 33, "text": " Third one."}
  ],
  "warnings": []
}
```

### Slice by speaker grouping

Input text:

```
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
```

User prompt:

```
Return things that the agent said grouped together, and things the customer said in separate groups.
```

Expected behavior: slices are grouped into one agent segment and one customer segment.

Example snippet:

Internal protocol excerpt:

**Internal protocol (excerpt):**

```
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: insert <slice/> markers
at the boundaries of the returned slices in the current text.
Current text:
---
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
---
```

User prompt:

**User prompt:**

```
Return things that the agent said grouped together, and things the customer said in separate groups.
```

Input text:

**Input text:**

```
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
```

Marked-up text:

**Marked-up text:**

```
Agent: Hello. Agent: I can help.<slice/> Customer: I need support. Customer: Thanks.
```

Structured data:

**Structured data (result):**

```
{
  "marked_up_text": "Agent: Hello. Agent: I can help.<slice/> Customer: I need support. Customer: Thanks.",
  "slices": [
    {"index": 1, "start_char": 0, "end_char": 30, "text": "Agent: Hello. Agent: I can help."},
    {"index": 2, "start_char": 30, "end_char": 72, "text": " Customer: I need support. Customer: Thanks."}
  ],
  "warnings": []
}
```

## Validation rules

Biblicus rejects:

- Non-tool responses.
- Insertions that are not `<slice/>` markers.
- Any modification to the original text.
- Empty tool arguments.

## Testing

Text slice supports two modes of testing:

- **Mocked unit tests** using a fake OpenAI client.
- **Integration tests** that call the live model and apply real edits.

See `features/text_slice.feature` and `features/integration_text_slice.feature`.

# Text extract

Text extract is a reusable utility for extracting spans from long texts with a language model without requiring the model to
re-emit every token. Instead of asking for a fully labeled transcript, Biblicus asks the model to insert XML tags into
an in-memory copy of the text. The model returns a small edit script (str_replace only), and Biblicus applies it and
parses the result into spans.

Text extract is part of a growing library of text utilities that focus on reliability, validation, and
reusable structure.

## How text extract works

1) Biblicus loads the full text into memory.
2) The model receives the text and returns an **edit script** with str_replace operations.
3) Biblicus applies the operations and validates that only tags were inserted.
4) The marked-up string is parsed into ordered **spans**.

The model never re-emits the full text, which lowers cost and reduces timeouts on long documents.

### Mechanism example

Start with a system prompt that defines the edit protocol and embeds the current text:

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

Then provide a short user prompt describing what to return:

```
USER PROMPT:
Return all the verbs.
```

The input text is the same content embedded in the system prompt:

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

## Data model

Text extract uses Pydantic models for strict validation:

- `TextExtractRequest`: input text + LLM config + prompt template.
- `TextExtractResult`: marked-up text and extracted spans.

System prompts must include `{text}`. Both system prompts and prompt templates support `{text_length}` placeholders
(plus `{error}` for retry hints). Prompt templates must not include `{text}` and should only describe what to return.

The structured output contains **spans only**. Any interstitial text remains in the marked-up string.

Text extract expects tags to land on word boundaries. Prompts should instruct the model to avoid inserting tags
inside words so spans stay aligned to human-readable text.

## Output contract

Text extract is tool-driven. The model must use tool calls instead of returning JSON in the assistant message.

Tool call arguments:

```
str_replace(old_str="Hello world", new_str="<span>Hello world</span>")
done()
```

Rules:

- Use the str_replace tool only.
- Each old_str must match exactly once.
- Each new_str must be the same text with span tags inserted.
- Only `<span>` and `</span>`.
- No modification of the original text.

## Example: Python API

```
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import TextExtractRequest, apply_text_extract

system_prompt = \"\"\"\nYou are a virtual file editor. Use the available tools to edit the text.\nInterpret the word “return” in the user’s request as: wrap the returned text\nwith <span>...</span> in-place in the current text.\n\nUse the str_replace tool to insert <span>...</span> tags and the done tool\nwhen finished. When finished, call done. Do NOT return JSON in the assistant message.\n\nRules:\n- Use str_replace only.\n- old_str must match exactly once in the current text.\n- old_str and new_str must be non-empty strings.\n- new_str must be identical to old_str with only <span> and </span> inserted.\n- Do not include <span> or </span> inside old_str or new_str.\n- Do not insert nested spans.\n- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n- Do not delete, reorder, paraphrase, or label text.\n\nCurrent text:\n---\n{text}\n---\n\"\"\".strip()

request = TextExtractRequest(
    text="Hello world",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model="gpt-4o-mini"),
    system_prompt=system_prompt,
    prompt_template="Return the entire text.",
)
result = apply_text_extract(request)
```

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
Hello world.
---
```

User prompt:

```
USER PROMPT:
Return the entire text.
```

Input text:

```
INPUT TEXT:
Hello world.
```

Marked-up text:

```
MARKED-UP TEXT:
<span>Hello world.</span>
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span>Hello world.</span>",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 12, "text": "Hello world."}
  ],
  "warnings": []
}
```

## Example: Verb markup task

```
system_prompt = \"\"\"\nYou are a virtual file editor. Use the available tools to edit the text.\nInterpret the word “return” in the user’s request as: wrap the returned text\nwith <span>...</span> in-place in the current text.\n\nUse the str_replace tool to insert <span>...</span> tags and the done tool\nwhen finished. When finished, call done. Do NOT return JSON in the assistant message.\n\nRules:\n- Use str_replace only.\n- old_str must match exactly once in the current text.\n- old_str and new_str must be non-empty strings.\n- new_str must be identical to old_str with only <span> and </span> inserted.\n- Do not include <span> or </span> inside old_str or new_str.\n- Do not insert nested spans.\n- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n- Do not delete, reorder, paraphrase, or label text.\n\nCurrent text:\n---\n{text}\n---\n\"\"\".strip()

prompt_template = \"\"\"\nReturn the verbs.\nInclude auxiliary verbs and main verbs.\nPreserve all whitespace and punctuation.\n\"\"\".strip()

request = TextExtractRequest(
    text=\"I can try to get help, but I promise nothing.\",
    client=LlmClientConfig(provider=AiProvider.OPENAI, model=\"gpt-4o-mini\"),
    system_prompt=system_prompt,
    prompt_template=prompt_template,
)
result = apply_text_extract(request)
```

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
I can try to get help, but I promise nothing.
---
```

User prompt:

```
USER PROMPT:
Return the verbs.
```

Input text:

```
INPUT TEXT:
I can try to get help, but I promise nothing.
```

Marked-up text:

```
MARKED-UP TEXT:
I <span>can</span> <span>try</span> to <span>get</span> help, but I <span>promise</span> nothing.
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "I <span>can</span> <span>try</span> to <span>get</span> help, but I <span>promise</span> nothing.",
  "spans": [
    {"index": 1, "start_char": 2, "end_char": 5, "text": "can"},
    {"index": 2, "start_char": 6, "end_char": 9, "text": "try"},
    {"index": 3, "start_char": 13, "end_char": 16, "text": "get"},
    {"index": 4, "start_char": 29, "end_char": 36, "text": "promise"}
  ],
  "warnings": []
}
```

## Integration examples

These examples mirror the integration tests and show the minimal user prompts that drive the tool loop.

### Extract paragraphs

Input text:

```
Para one. || Para two. || Para three.
```

User prompt:

```
Return each paragraph.
```

Expected behavior: the model inserts `<span>...</span>` around each paragraph.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
Para one. || Para two. || Para three.
---
```

User prompt:

```
USER PROMPT:
Return each paragraph.
```

Input text:

```
INPUT TEXT:
Para one. || Para two. || Para three.
```

Marked-up text:

```
MARKED-UP TEXT:
<span>Para one.</span> || <span>Para two.</span> || <span>Para three.</span>
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span>Para one.</span> || <span>Para two.</span> || <span>Para three.</span>",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 9, "text": "Para one."},
    {"index": 2, "start_char": 13, "end_char": 22, "text": "Para two."},
    {"index": 3, "start_char": 26, "end_char": 37, "text": "Para three."}
  ],
  "warnings": []
}
```

### Extract first sentences per paragraph

Input text:

```
First one. Second one. || Alpha first. Alpha second.
```

User prompt:

```
Return the first sentence from each paragraph.
```

Expected behavior: the model wraps the first sentence of each paragraph in spans.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
First one. Second one. || Alpha first. Alpha second.
---
```

User prompt:

```
USER PROMPT:
Return the first sentence from each paragraph.
```

Input text:

```
INPUT TEXT:
First one. Second one. || Alpha first. Alpha second.
```

Marked-up text:

```
MARKED-UP TEXT:
<span>First one.</span> Second one. || <span>Alpha first.</span> Alpha second.
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span>First one.</span> Second one. || <span>Alpha first.</span> Alpha second.",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 10, "text": "First one."},
    {"index": 2, "start_char": 27, "end_char": 39, "text": "Alpha first."}
  ],
  "warnings": []
}
```

### Extract money quotes

Input text:

```
She said "PAYMENT_QUOTE_001: I will pay $20 today." Then she left.
```

User prompt:

```
Return the quoted payment statement exactly as written, including the quotation marks.
```

Expected behavior: the quoted statement is wrapped in a span and preserved verbatim.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
She said "PAYMENT_QUOTE_001: I will pay $20 today." Then she left.
---
```

User prompt:

```
USER PROMPT:
Return the quoted payment statement exactly as written, including the quotation marks.
```

Input text:

```
INPUT TEXT:
She said "PAYMENT_QUOTE_001: I will pay $20 today." Then she left.
```

Marked-up text:

```
MARKED-UP TEXT:
She said <span>"PAYMENT_QUOTE_001: I will pay $20 today."</span> Then she left.
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "She said <span>\"PAYMENT_QUOTE_001: I will pay $20 today.\"</span> Then she left.",
  "spans": [
    {"index": 1, "start_char": 9, "end_char": 52, "text": "\"PAYMENT_QUOTE_001: I will pay $20 today.\""}
  ],
  "warnings": []
}
```

### Extract verbs

Input text:

```
We run fast. They agree.
```

User prompt:

```
Return all the verbs.
```

Expected behavior: each verb is wrapped in a span without splitting words.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
We run fast. They agree.
---
```

User prompt:

```
USER PROMPT:
Return all the verbs.
```

Input text:

```
INPUT TEXT:
We run fast. They agree.
```

Marked-up text:

```
MARKED-UP TEXT:
We <span>run</span> fast. They <span>agree</span>.
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "We <span>run</span> fast. They <span>agree</span>.",
  "spans": [
    {"index": 1, "start_char": 3, "end_char": 6, "text": "run"},
    {"index": 2, "start_char": 23, "end_char": 28, "text": "agree"}
  ],
  "warnings": []
}
```

### Extract grouped speaker statements

Input text:

```
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
```

User prompt:

```
Return things that the agent said grouped together, and things the customer said in separate groups.
```

Expected behavior: agent text is grouped in one span and customer text in another.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
---
```

User prompt:

```
USER PROMPT:
Return things that the agent said grouped together, and things the customer said in separate groups.
```

Input text:

```
INPUT TEXT:
Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks.
```

Marked-up text:

```
MARKED-UP TEXT:
<span>Agent: Hello. Agent: I can help.</span> <span>Customer: I need support. Customer: Thanks.</span>
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span>Agent: Hello. Agent: I can help.</span> <span>Customer: I need support. Customer: Thanks.</span>",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 33, "text": "Agent: Hello. Agent: I can help."},
    {"index": 2, "start_char": 34, "end_char": 78, "text": "Customer: I need support. Customer: Thanks."}
  ],
  "warnings": []
}
```

## Example: Markov analysis segmentation

Use the `span_markup` segmentation method in Markov recipes.

Example snippet:

System prompt excerpt:

```
SYSTEM PROMPT (excerpt):
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
Greeting. Verification. Resolution.
---
```

User prompt:

```
USER PROMPT:
Return the segments that represent contiguous phases in the text.
```

Input text:

```
INPUT TEXT:
Greeting. Verification. Resolution.
```

Marked-up text:

```
MARKED-UP TEXT:
<span>Greeting.</span> <span>Verification.</span> <span>Resolution.</span>
```

Structured data:

```
STRUCTURED DATA (result):
{
  "marked_up_text": "<span>Greeting.</span> <span>Verification.</span> <span>Resolution.</span>",
  "spans": [
    {"index": 1, "start_char": 0, "end_char": 10, "text": "Greeting."},
    {"index": 2, "start_char": 11, "end_char": 24, "text": "Verification."},
    {"index": 3, "start_char": 25, "end_char": 37, "text": "Resolution."}
  ],
  "warnings": []
}
```

Recipe example (text extract provider-backed):

```
schema_version: 1
segmentation:
  method: span_markup
  span_markup:
    client:
      provider: openai
      model: gpt-4o-mini
      api_key: null
      response_format: json_object
    system_prompt: |
      You are a virtual file editor. Use the available tools to edit the text.
      Interpret the word “return” in the user’s request as: wrap the returned text
      with <span>...</span> in-place in the current text.

      Use the str_replace tool to insert <span>...</span> tags and the done tool
      when finished. When finished, call done. Do NOT return JSON in the assistant message.

      Rules:
      - Use str_replace only.
      - old_str must match exactly once in the current text.
      - old_str and new_str must be non-empty strings.
      - new_str must be identical to old_str with only <span> and </span> inserted.
      - Do not include <span> or </span> inside old_str or new_str.
      - Do not insert nested spans.
      - If a tool call fails due to non-unique old_str, retry with a longer unique old_str.
      - If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.
      - Do not delete, reorder, paraphrase, or label text.
      Current text:
      ---
      {text}
      ---
    prompt_template: |
      Return the segments that represent contiguous phases in the text.

      Rules:
      - Preserve original order.
      - Do not add labels, summaries, or commentary.
      - Prefer natural boundaries like greeting/opening, identity verification, reason for call,
        clarification, resolution steps, handoff/escalation, closing.
      - Use speaker turn changes as possible boundaries, but keep multi-turn exchanges together if they
        form a single phase.
      - Avoid extremely short fragments; merge tiny leftovers into a neighboring span.
model:
  family: gaussian
  n_states: 4
observations:
  encoder: tfidf
```

## Validation rules

Biblicus rejects:

- Non-JSON responses.
- Insertions that are not span tags.
- Nested or unbalanced tags.
- Any modification to the original text.

## Testing

Text extract supports two modes of testing:

- **Mocked unit tests** using a fake OpenAI client.
- **Integration tests** that call the live model and apply real edits.

See `features/text_extract.feature` and `features/integration_text_extract.feature`.

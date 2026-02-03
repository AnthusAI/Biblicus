# Text utilities

You need to extract quotes, segments, or entities from a document so you can use them in your application logic.

The obvious approach is to paste the text into a prompt and ask a model to "return a JSON list of quotes." That works for short texts, but it fails in production for three reasons:

1.  **Hallucination risk**: Models often hallucinate quotes based on your few-shot examples or paraphrase the text instead of extracting it verbatim.
2.  **Output token cost**: Repeating the text back to you is slow and expensive. If you want to extract 50 sentences from a document, you pay for generating all those tokens again.
3.  **Transcription errors**: The longer the completion, the higher the chance of a typo or drift, making it hard to match the result back to the source reliability.

## The old way: "Just return JSON"

In this example, you want to extract payment terms. The prompt includes few-shot examples to show the desired JSON format.

**Input text:**

```text
The project was originally scheduled for Q1 but was delayed by three weeks
due to supply chain issues. We will pay the full amount of $5,000 upon
completion of the final milestone, subject to inspection.
```

**Prompt:**

```text
Extract payment terms from the text. Return a JSON list of strings.
Example: ["Payment of $100 due immediately", "Net 30 terms apply"]
```

**The problem:**

The model sees the few-shot examples and hallucinates a quote that isn't in the text because it "looks like" a payment term, or it paraphrases the real quote.

**Model output (incorrect):**

```json
[
  "Payment of $100 due immediately",
  "We will pay $5,000 when finished"
]
```

*(Note: The first item was hallucinated from the few-shot example, and the second was paraphrased instead of quoted exacty.)*

This output is useless for a reliable pipeline because you can't trust the values.

## The Virtual File Pattern

Biblicus text utilities solve this by **getting on the same page** with the model. Instead of asking the model to repeat the text, you give it a **virtual file** that you both can see. The model adds XML markup to the file in-place (like `<quote>...</quote>` or `<slice/>`), and Biblicus parses the marked-up file to return structured data.

**The Solution:**

The model edits the text in-place using a tool. It doesn't generate new text; it just points to the existing text.

**Model action (correct):**

```python
str_replace(
    old_str="We will pay the full amount of $5,000 upon completion of the final milestone, subject to inspection.",
    new_str="<span>We will pay the full amount of $5,000 upon completion of the final milestone, subject to inspection.</span>"
)
```

**Virtual File State (in-memory):**

The file now contains the markup. This is what the parser sees.

```text
The project was originally scheduled for Q1 but was delayed by three weeks
due to supply chain issues. <span>We will pay the full amount of $5,000 upon
completion of the final milestone, subject to inspection.</span>
```

**Biblicus output:**

```json
{
  "spans": [
    {
      "text": "We will pay the full amount of $5,000 upon completion of the final milestone, subject to inspection.",
      "start_char": 103,
      "end_char": 203
    }
  ]
}
```

Now that the file is marked up, Biblicus uses a simple, deterministic XML parser to find the tags and extract the content they wrap. This means the output `text` is guaranteed to be a substring of the original document, and the `start_char` / `end_char` indices are mathematically precise.

This pattern enables the model to coordinate with your harness procedure about specific details in the text without regenerating the content tokens. It is faster, cheaper, and more reliable because the text itself is never re-emitted.

## Internal patterns

This virtual file pattern is a generalized mechanism used to implement multiple extraction patterns. Different utilities use different markup strategies to achieve specific goals. You don't need to implement these, but understanding them helps you choose the right tool.

-   **Extract**: Return exact spans (quotes, entities) by wrapping them in tags.
    -   Markup: `<span>...</span>`
    -   Example: `We <span>run</span> fast.`
    -   See: `docs/TEXT_EXTRACT.md`

-   **Slice**: Split text into ordered segments by inserting boundary markers.
    -   Markup: `<slice/>`
    -   Example: `First.<slice/> Second.`
    -   See: `docs/TEXT_SLICE.md`

-   **Annotate**: Label spans with attributes (semantic markup) by adding attributes to tags.
    -   Markup: `<span label="verb">...</span>`
    -   Example: `We <span label="verb">run</span> fast.`
    -   See: `docs/TEXT_ANNOTATE.md`

-   **Redact**: Identify spans for removal.
    -   Markup: `<span redact="pii">...</span>`
    -   Example: `Contact <span redact="pii">name@example.com</span>.`
    -   See: `docs/TEXT_REDACT.md`

-   **Link**: Connect spans with ID/REF attributes.
    -   Markup: `<span id="1">...</span>...<span ref="1">...</span>`
    -   Example: `<span id="1">Acme</span>... <span ref="1">Acme</span>`
    -   See: `docs/TEXT_LINK.md`

## The virtual file editor pattern

Text utilities work by treating the input text as an in-memory file. Biblicus supplies the editing protocol internally
and the model edits the file using tool calls:

- `str_replace(old_str, new_str)`
- `view()`
- `done()`

The model does **not** re-emit the whole document. It only inserts markup into the existing text. Biblicus validates the
edits and parses the marked-up text into structured output.

This gives you:

- Lower cost and faster execution on long documents.
- Deterministic validation (no hidden edits).
- Clear failure modes when the model misbehaves.

## Long-span handling

For long spans, Biblicus instructs the model to insert the opening and closing tags in **separate** `str_replace` calls. This avoids asking the model to emit long quoted passages just to wrap them. For short spans (a few words), the model is allowed to insert both tags in a single call.

This behavior is built into the system prompts for span-based utilities (**extract**, **annotate**, **redact**, **link**) and is covered by unit tests:

- `tests/test_text_extract_tool_calls.py`
- `tests/test_text_utility_tool_calls.py`

### Mechanism example

The user prompt focuses only on what to return:

**Internal protocol (excerpt):**

```text
You are a virtual file editor. Use the available tools to edit the text.
Interpret the word "return" in the user's request as: wrap the returned text with
<span>...</span> in-place in the current text.
Current text:
---
The project was originally scheduled for Q1 but was delayed by three weeks
due to supply chain issues. We will pay the full amount of $5,000 upon
completion of the final milestone, subject to inspection.
---
```

**User prompt:**

```text
Return the payment terms.
```

**Input text:**

```text
The project was originally scheduled for Q1 but was delayed by three weeks
due to supply chain issues. We will pay the full amount of $5,000 upon
completion of the final milestone, subject to inspection.
```

The model edits the virtual file by inserting tags in-place:

**Marked-up text:**

```text
The project was originally scheduled for Q1 but was delayed by three weeks
due to supply chain issues. <span>We will pay the full amount of $5,000 upon
completion of the final milestone, subject to inspection.</span>
```

Biblicus returns structured data parsed from the markup:

**Structured data:**

```json
{
  "marked_up_text": "The project was originally scheduled for Q1 but was delayed by three weeks\ndue to supply chain issues. <span>We will pay the full amount of $5,000 upon\ncompletion of the final milestone, subject to inspection.</span>",
  "spans": [
    {
      "index": 1,
      "start_char": 103,
      "end_char": 203,
      "text": "We will pay the full amount of $5,000 upon completion of the final milestone, subject to inspection."
    }
  ],
  "warnings": []
}
```

## Prompt contract

The prompt contract is intentionally simple:

- **User prompt**: describes *what to return* (for example, “Return all verbs.”).

Biblicus supplies the editing protocol internally, so most callers only provide the user prompt and the input text.
Override the internal protocol only if you need to change the mechanics.

## Validation and confirmation

Biblicus validates the marked-up output syntactically. If the markup fails to parse or violates the rules, Biblicus
adds a feedback message to the conversation history (including prior tool calls) and retries.

When a tool produces zero spans/markers, Biblicus asks the model to confirm the empty result. If the model confirms,
Biblicus returns the empty result with a warning instead of raising an error.

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
  - Example: "Link repeated mentions of the same company to the first mention."

These utilities are intentionally simple at the prompt layer, even though they share the same internal tool loop.

## Safeguards and feedback

The tool loop adds automatic safeguards before applying edits. When a safeguard trips, Biblicus sends a feedback message and asks the model to try again.

- **Unique match required**: `old_str` must match exactly once in the current text.
- **No-op edits rejected**: `old_str` and `new_str` must differ.
- **Text preservation enforced**: replacements may only insert markup tags; the underlying text must stay the same.
- **Short substring guidance**: if `old_str` is very short, the feedback advises calling `view()` to choose a longer unique substring.

Test coverage for these safeguards lives in `tests/test_tool_loop_safeguards.py`.

### Reliable coordination: system prompts and feedback

Models are stochastic. They can miss quote boundaries, make up attributes, or hallucinate text despite your instructions.

Biblicus utilities mitigate this with a **closed-loop retry mechanism**.

1.  **System prompt**: Defines the "rules of the game" (e.g., "Use `<slice/>` markers to split text," "Do not change the original text").
2.  **User message**: Provides the specific instruction (e.g., "Slice by sentence," "Extract all verbs").
3.  **Parser validation**: When the model returns a tool call, the harness applies it to the virtual file and attempts to parse the result.
4.  **Feedback loop**: If the edit fails (e.g., `str_replace` cannot find the `old_str`) or the markup is invalid (e.g., nested tags where forbidden), the harness **catches the error** and sends it back to the model as a new user message.
5.  **Retry**: The model sees the error ("Error: string not found") and tries again with corrected parameters.

### Feedback examples (retry stories)

Each example shows the **incorrect tool call**, the **feedback message** the harness sends, and the **corrected tool call** on retry.

**Scenario 1: ambiguous match**

In this scenario, the model wants to insert an XML markup tag but it wasn't specific enough. It tries to target the word "the", which appears multiple times in the text. This is an example of where the programmatic harness responds by saying basically: "Excuse me, but you're going to have to be more specific..."

The harness detects the ambiguity (3 matches) and rejects the edit, forcing the model to try again with enough context to be unique.

Incorrect tool call:

```text
str_replace(old_str="the", new_str="<span>the</span>")
```

Harness feedback:

```text
Your last tool call failed.
Error: Tool loop requires old_str to match exactly once (found 3 matches)
Use a longer unique old_str by including surrounding words or punctuation so it matches exactly once.
```

Corrected tool call:

```text
str_replace(
  old_str="the full amount",
  new_str="<span>the full amount</span>"
)
```

**Scenario 2: no-op edit**

Sometimes models "spin their wheels" by emitting tool calls that don't actually change anything. Here, the model calls `str_replace` with identical `old_str` and `new_str` values.

The harness catches this wasted effort and prompts the model to make a real change (or call `done` if it's finished).

Incorrect tool call:

```text
str_replace(
  old_str="We will pay the full amount",
  new_str="We will pay the full amount"
)
```

Harness feedback:

```text
Your last tool call failed.
Error: Tool loop requires str_replace to make a change
Fix the tool call and try again.
```

Corrected tool call:

```text
str_replace(
  old_str="We will pay the full amount",
  new_str="<span>We will pay the full amount</span>"
)
```

**Scenario 3: text modification**

One of the most dangerous failure modes is when a model rewrites the content instead of just marking it up. Here, the model capitalizes "Subject" in the replacement string, which would corrupt the original document.

The harness enforces strict text preservation: the characters outside the tags must match the original exactly. It rejects the edit and tells the model to keep the underlying text the same.

Incorrect tool call:

```text
str_replace(
  old_str="subject to inspection.",
  new_str="<span>Subject to inspection.</span>"
)
```

Harness feedback:

```text
Your last tool call failed.
Error: Tool loop replacements may only insert markup tags; the underlying text must stay the same
Fix the tool call and try again.
```

Corrected tool call:

```text
str_replace(
  old_str="subject to inspection.",
  new_str="<span>subject to inspection.</span>"
)
```

**Scenario 4: missing substring**

Models sometimes hallucinate quotes or make small transcription errors (like "Net 45" instead of "Net 30").

The harness attempts to locate `old_str` in the current text. When it finds 0 matches, it tells the model the substring doesn't exist and suggests copying the text exactly as it appears.

Incorrect tool call:

```text
str_replace(
  old_str="Net 30 terms",
  new_str="<span>Net 30 terms</span>"
)
```

Harness feedback:

```text
Your last tool call failed.
Error: Tool loop requires old_str to match exactly once (found 0 matches)
Copy the exact old_str from the current text (including punctuation/case) or call view to inspect the latest text.
```

Corrected tool call:

```text
str_replace(
  old_str="We will pay the full amount",
  new_str="<span>We will pay the full amount</span>"
)
```

### Why the safeguards matter

If you are using a large, highly capable model, some of these guardrails may feel redundant. But in information-management workflows you often want to run **smaller models** frequently, or keep sensitive text out of a third-party inference service. In those cases, smaller models are more likely to make small, mechanical errors.

The harness safeguards make those errors recoverable. Deterministic checks catch the mistake, send precise feedback, and let the model correct itself. That is what makes lightweight, local, or cost-efficient models viable for real-world extraction and markup tasks.

This alignment—between the system prompt's rules, the user's intent, and the parser's validation logic—is complex to implement from scratch. Biblicus provides these pre-packaged, battle-tested implementations so you can just use the utility.

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

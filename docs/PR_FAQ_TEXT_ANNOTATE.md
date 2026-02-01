# PR-FAQ (draft): Text annotate

## Press release

### Headline

Biblicus adds text annotate: attributed spans using the virtual file editor pattern.

### Summary

Biblicus now supports **text annotate**, a utility that lets a language model mark spans of text and attach simple
attributes (for example, phase, role, or evidence type) without re-emitting the full document. This builds on the same
virtual file editor pattern used by text extract and text slice, but only when attributes are required.

### Customer quote

“Text annotate gives us structured attributes without forcing a full rewrite. We can keep the original text intact while
capturing the labels we need.”

### What’s new

- A new utility: `biblicus.text.annotate`.
- A dedicated prompt contract that is simple and focused on a single labeling task.
- Strict validation that ensures only attributes were added and the original text is preserved.

### Availability

Text annotate is available as a Python API utility and supports the same tool-loop integration test approach as existing
text utilities.

---

## FAQ

### What problem does this solve?

Some ETL pipelines need **labeled spans**, not just extracted spans. For example, you may want phases of a conversation
(greeting, verification, resolution) or roles (agent vs customer). Existing extract/slice utilities can return spans, but
they cannot attach structured attributes in a consistent way.

Text annotate provides a standardized way to attach attributes while preserving the original text.

### How does it work?

It uses the same virtual file editor pattern as text extract:

1) Load the full text into an in-memory file.
2) The model inserts `<span>` tags with **attributes** using `str_replace`.
3) Biblicus validates that only tags/attributes were inserted.
4) The result is parsed into attributed spans.

### How is it different from text extract?

- **Extract** returns spans only (no attributes).
- **Annotate** returns spans with attributes (when labels are required).

This keeps prompts simple for small models by using annotate only when needed.

### What’s the prompt contract?

- **System prompt**: explains the tool loop and the attribute schema.
- **User prompt**: describes what to return (for example, “Return phases with attribute phase=…”).

The system prompt contains all markup details; the user prompt stays short.

### What attributes are supported?

Attributes are specified per-request. Examples:

- `phase`: greeting, verification, resolution
- `role`: agent, customer
- `evidence`: request, promise, denial

The allowed attribute names and values are validated in code.

### Is this a replacement for NER or classification models?

No. It is a **text utility** for structured annotation within a single document. It’s designed for ETL pipelines that
need deterministic output and traceability, not generalized model training.

### How do we validate correctness?

- Attributes must match an allowed schema.
- The source text must be preserved exactly (tags only).
- Tags must be well-formed and non-overlapping.
- Tests run in mocked and integration modes.

### What’s the failure mode?

If the model returns invalid edits, Biblicus rejects the output with a clear error and a retry hint. No partial results are
silently accepted.

### Why not just use JSON output?

The virtual file editor pattern avoids re-emitting the full document, which reduces token cost and improves reliability
on long texts. It also allows deterministic validation of the original text.

### How does this fit the existing utilities?

- **Extract**: spans without attributes.
- **Slice**: ordered segments.
- **Annotate**: spans with attributes.

The internal tool-loop remains the same; only the prompt contract and validation rules change.

### What’s out of scope for v1?

- Cross-document linking.
- Multi-layer annotations.
- Overlapping spans.
- Arbitrary tag names or free-form attribute schemas.

### What are the next steps if approved?

1) Document the utility and prompt contract.
2) Write behavior specs for annotate.
3) Implement parsing and validation for attributed spans.
4) Add integration tests mirroring real prompts.

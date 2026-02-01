# Mark Sensitive Text for Redaction

This tutorial demonstrates an “agentic text utility” workflow:

- Biblicus provides the model a tool loop that can edit a virtual file in memory.
- Your prompt says what to return.
- The utility returns both the marked-up text and structured span data.

## Run it (mock mode)

Mock mode is deterministic and requires no API keys.

```bash
rm -rf corpora/use_case_text_redact
python scripts/use_cases/text_redact_demo.py --corpus corpora/use_case_text_redact --force --mock
```

## Run it (real model)

Real mode requires `OPENAI_API_KEY` in your environment.

```bash
rm -rf corpora/use_case_text_redact
export OPENAI_API_KEY="…"
python scripts/use_cases/text_redact_demo.py --corpus corpora/use_case_text_redact --force
```

## What you should see

The script prints a JSON object to standard output.

You should see the original text with `<span>...</span>` markers inserted:

```json
{
  "marked_up_text": "Please call me at <span>555-0100</span> and email <span>sam@example.com</span>."
}
```

You should also see structured spans extracted from the marked-up text:

```json
{
  "spans": [
    { "index": 1, "text": "555-0100" },
    { "index": 2, "text": "sam@example.com" }
  ]
}
```


# Notes to Context Pack

This tutorial shows the smallest complete loop:

1. Ingest a few short notes into a corpus.
2. Retrieve evidence using a deterministic lexical backend.
3. Build a context pack from that evidence and fit it to a token budget.

## Run it

```bash
rm -rf corpora/use_case_notes
python scripts/use_cases/notes_to_context_pack_demo.py --corpus corpora/use_case_notes --force
```

## What you should see

The script prints a JSON object to standard output.

First, you should see retrieval evidence. The evidence is structured and includes provenance.

```json
{
  "evidence": [
    {
      "item_id": "…",
      "score": 1.0,
      "text": "Primary button style preference: favorite color is magenta.",
      "source": { "uri": "…" }
    }
  ]
}
```

Then you should see a fitted context pack. This is the text you would pass into an upstream model
request.

```json
{
  "context_pack_text": "Primary button style preference: favorite color is magenta."
}
```

## How it works

This tutorial uses the `scan` backend, which is deterministic and runs without building an index.
It is a useful baseline when you want repeatable behavior while you learn the system.


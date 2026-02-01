# Folder Search With Extraction

This tutorial simulates a common workflow: you are handed a folder of text files and need to
extract, index, and retrieve evidence.

## Run it

```bash
rm -rf corpora/use_case_text_folder
python scripts/use_cases/text_folder_search_demo.py --corpus corpora/use_case_text_folder --force
```

## What you should see

The script prints a JSON object to standard output.

You should see evidence that includes text from a retrieved document:

```json
{
  "query_text": "Beta unique signal for retrieval lab",
  "evidence": [
    {
      "text": "Beta unique signal for retrieval lab.",
      "score": 1.0
    }
  ]
}
```

## How it works

This tutorial runs an extraction pipeline with a single step:

- `pass-through-text` reads the text of existing text items.

Then it builds a `sqlite-full-text-search` retrieval run using the latest extraction run as the
indexing source.


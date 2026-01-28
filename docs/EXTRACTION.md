# Text extraction

Text extraction is a separate pipeline stage that produces derived text artifacts under a corpus.

This separation matters because it lets you combine extraction choices and retrieval backends independently.

## What extraction produces

An extraction run produces:

- A run manifest
- Per item extracted text files for the items that produced usable text

Extraction artifacts are stored under the corpus:

```
corpus/
  .biblicus/
    runs/
      extraction/
        <extractor id>/
          <run id>/
            manifest.json
            text/
              <item id>.txt
```

## Built in extractors

Version zero includes a small set of deterministic extractors.

`pass-through-text`

- Reads text items and returns their content
- For Markdown items, it strips YAML front matter and returns only the body
- Skips non text items

`metadata-text`

- Builds a small text representation from catalog metadata
- This is useful when you have a non text item with meaningful tags or a title

## Cascade extractor pipeline

The `cascade` extractor composes multiple extractors into an explicit pipeline.

The pipeline tries each step in order:

- If a step returns no text for an item, the pipeline tries the next step.
- If a step returns empty or whitespace text, the pipeline treats it as unusable and tries the next step.
- If a step returns usable text, later steps are not run for that item.

This lets you build a strict, explicit extraction policy. It also lets you compare extraction strategies using the same corpus.

## Example: extract from a corpus

```
rm -rf corpora/extraction-demo
python3 -m biblicus init corpora/extraction-demo

printf 'x' > /tmp/image.png
python3 -m biblicus ingest --corpus corpora/extraction-demo /tmp/image.png --tag extracted

python3 -m biblicus extract --corpus corpora/extraction-demo --extractor cascade \\
  --step pass-through-text \\
  --step metadata-text
```

The extracted text for the image comes from the `metadata-text` step because the image is not a text item.

## Use extracted text in retrieval

Retrieval backends can build and query using a selected extraction run. This is configured by passing `extraction_run=extractor_id:run_id` to the backend build command.

```
python3 -m biblicus build --corpus corpora/extraction-demo --backend sqlite-full-text-search \\
  --config extraction_run=cascade:EXTRACTION_RUN_ID
python3 -m biblicus query --corpus corpora/extraction-demo --query extracted
```

## What extraction is not

Text extraction does not mutate the raw corpus. It is derived output that can be regenerated and compared across implementations.

Future extractors will likely include Portable Document Format text extraction and optical character recognition for images, but those remain separate from raw ingestion for reproducibility and comparison.


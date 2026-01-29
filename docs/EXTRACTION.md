# Text extraction

Text extraction is a separate pipeline stage that produces derived text artifacts under a corpus.

This separation matters because it lets you combine extraction choices and retrieval backends independently.

## What extraction produces

An extraction run produces:

- A run manifest
- Per item extracted text files for the final output
- Per step extracted text artifacts for all pipeline steps
- Per item result status, including extracted, skipped, and errored outcomes

Extraction artifacts are stored under the corpus:

```
corpus/
  .biblicus/
    runs/
      extraction/
        pipeline/
          <run id>/
            manifest.json
            text/
              <item id>.txt
            steps/
              01-pass-through-text/
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

`pdf-text`

- Attempts to extract text from Portable Document Format items
- Skips items that are not Portable Document Format
- Uses the `pypdf` library
- Produces empty output for scanned Portable Document Format files that contain no extractable text without optical character recognition

`select-text`

- Selects extracted text artifacts from earlier pipeline steps
- This is used when you have multiple pipeline steps that can produce usable text for the same items and you want one chosen result
- Records which step supplied the selected text

`unstructured`

- Broad document text extraction backed by the optional `unstructured` dependency
- Intended as a last-resort extractor for non-text items when more specific extractors cannot produce usable text
- Skips items that are already text so the pass-through extractor remains the canonical choice for text items

To install:

```
python3 -m pip install "biblicus[unstructured]"
```

`markitdown`

- Converts common document formats into Markdown-like text
- Backed by the optional `markitdown` dependency
- Requires Python 3.10 or higher
- Skips items that are already text so the pass-through extractor remains the canonical choice for text items
- This means it will not process `text/html` or other text media types unless that policy changes

To install:

```
python3 -m pip install "biblicus[markitdown]"
```

Example:

```
python3 -m biblicus extract build --corpus corpora/extraction-demo \\
  --step markitdown
```

`ocr-rapidocr`

- Optical character recognition for image items
- Backed by the optional `rapidocr-onnxruntime` dependency
- Intended as a practical default when you need text from images without running a service

To install:

```
python3 -m pip install "biblicus[ocr]"
```

`stt-openai`

- Speech to text transcription for audio items
- Backed by the optional `openai` dependency
- Requires an OpenAI API key (from `OPENAI_API_KEY` or the user configuration file)

To install:

```
python3 -m pip install "biblicus[openai]"
```

To configure:

- Create `~/.biblicus/config.yml` or `./.biblicus/config.yml` with:

```
openai:
  api_key: YOUR_KEY_HERE
```

## How selection chooses text

The `select-text` extractor does not attempt to judge extraction quality. It chooses the first usable text from prior pipeline outputs in pipeline order.

Usable means non-empty after stripping whitespace.

This means selection does not automatically choose the longest extracted text or the extraction with the most content. If you want a scoring rule such as choose the longest extracted text, that should be a separate selection extractor so the policy is explicit, versioned, and testable.

`select-longest-text`

- Selects the longest usable extracted text from earlier pipeline steps
- Useful when you have multiple competing extractors for the same item types and you want a deterministic “more content wins” policy

## Pipeline extractor

The `pipeline` extractor composes multiple extractors into an explicit pipeline.

The pipeline runs every step in order and records all step outputs. Each step receives the raw item and the outputs of all prior steps. The final extracted text is the last extracted output in pipeline order.

This lets you build explicit extraction policies while keeping every step outcome available for comparison and metrics.

## Complementary versus competing extractors

The pipeline is designed for complementary steps that do not overlap much in what they handle.

Examples of complementary steps:

- A text extractor that only applies to text items
- A Portable Document Format text extractor that only applies to `application/pdf`
- An optical character recognition extractor that applies to images and scanned Portable Document Format files
- A speech to text extractor that applies to audio items
- A metadata extractor that always applies but produces low fidelity fallback text

Competing extractors are different. Competing extractors both claim they can handle the same item type, but they might produce different output quality. When you want to compare or switch between competing extractors, make that decision explicit with a selection extractor step such as `select-text` or a custom selection extractor.

## Example: extract from a corpus

```
rm -rf corpora/extraction-demo
python3 -m biblicus init corpora/extraction-demo

printf 'x' > /tmp/image.png
python3 -m biblicus ingest --corpus corpora/extraction-demo /tmp/image.png --tag extracted

python3 -m biblicus extract build --corpus corpora/extraction-demo \\
  --step pass-through-text \\
  --step pdf-text \\
  --step metadata-text
```

The extracted text for the image comes from the `metadata-text` step because the image is not a text item.

## Example: selection within a pipeline

Selection is a pipeline step that chooses extracted text from previous pipeline steps. Selection is just another extractor in the pipeline, and it decides which prior output to carry forward.

```
python3 -m biblicus extract build --corpus corpora/extraction-demo \\
  --step pass-through-text \\
  --step metadata-text \\
  --step select-text
```

The pipeline run produces one extraction run under `pipeline`. You can point retrieval backends at that run.

## Inspecting and deleting extraction runs

Extraction runs are stored under the corpus and can be listed and inspected.

```
python3 -m biblicus extract list --corpus corpora/extraction-demo
python3 -m biblicus extract show --corpus corpora/extraction-demo --run pipeline:EXTRACTION_RUN_ID
```

Deletion is explicit and requires typing the exact run reference as confirmation:

```
python3 -m biblicus extract delete --corpus corpora/extraction-demo \\
  --run pipeline:EXTRACTION_RUN_ID \\
  --confirm pipeline:EXTRACTION_RUN_ID
```

## Use extracted text in retrieval

Retrieval backends can build and query using a selected extraction run. This is configured by passing `extraction_run=extractor_id:run_id` to the backend build command.

```
python3 -m biblicus build --corpus corpora/extraction-demo --backend sqlite-full-text-search \\
  --config extraction_run=pipeline:EXTRACTION_RUN_ID
python3 -m biblicus query --corpus corpora/extraction-demo --query extracted
```

## What extraction is not

Text extraction does not mutate the raw corpus. It is derived output that can be regenerated and compared across implementations.

Optical character recognition and speech to text are implemented as extractors so you can compare providers and configurations while keeping raw items immutable.

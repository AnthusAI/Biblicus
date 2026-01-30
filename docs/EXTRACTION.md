# Text Extraction Pipeline

Text extraction is a separate pipeline stage that produces derived text artifacts under a corpus.

This separation matters because it lets you combine extraction choices and retrieval backends independently.

For detailed documentation on specific extractors, see [Extractor Reference](extractors/index.md).

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

## Available Extractors

Biblicus provides 16 built-in extractors organized by category:

### Text & Document Processing

- [`pass-through-text`](extractors/text-document/pass-through.md) - Direct text file reading
- [`metadata-text`](extractors/text-document/metadata.md) - Text from item metadata
- [`pdf-text`](extractors/text-document/pdf.md) - PDF text extraction using pypdf
- [`markitdown`](extractors/text-document/markitdown.md) - Office documents via MarkItDown
- [`unstructured`](extractors/text-document/unstructured.md) - Universal document parsing

### Optical Character Recognition

- [`ocr-rapidocr`](extractors/ocr/rapidocr.md) - Fast ONNX-based OCR
- [`ocr-paddleocr-vl`](extractors/ocr/paddleocr-vl.md) - Advanced OCR with VL model

### Vision-Language Models

- [`docling-smol`](extractors/vlm-document/docling-smol.md) - SmolDocling-256M for fast document processing
- [`docling-granite`](extractors/vlm-document/docling-granite.md) - Granite Docling-258M for high-accuracy extraction

### Speech-to-Text

- [`stt-openai`](extractors/speech-to-text/openai.md) - OpenAI Whisper API
- [`stt-deepgram`](extractors/speech-to-text/deepgram.md) - Deepgram Nova-3 API

### Pipeline Utilities

- [`select-text`](extractors/pipeline-utilities/select-text.md) - First successful extractor
- [`select-longest-text`](extractors/pipeline-utilities/select-longest.md) - Longest output selection
- [`select-override`](extractors/pipeline-utilities/select-override.md) - Per-item override by ID
- [`select-smart-override`](extractors/pipeline-utilities/select-smart-override.md) - Media type-based routing
- [`pipeline`](extractors/pipeline-utilities/pipeline.md) - Multi-step extraction workflow

For detailed documentation including configuration options, usage examples, and best practices, see the [Extractor Reference](extractors/index.md).

## How selection chooses text

The `select-text` extractor does not attempt to judge extraction quality. It chooses the first usable text from prior pipeline outputs in pipeline order.

Usable means non-empty after stripping whitespace.

This means selection does not automatically choose the longest extracted text or the extraction with the most content. If you want a scoring rule such as choose the longest extracted text, use the [`select-longest-text`](extractors/pipeline-utilities/select-longest.md) extractor instead.

Other selection strategies include:

- [`select-override`](extractors/pipeline-utilities/select-override.md) - Override extraction for specific items by ID
- [`select-smart-override`](extractors/pipeline-utilities/select-smart-override.md) - Route items based on media type patterns

## Pipeline extractor

The `pipeline` extractor composes multiple extractors into an explicit pipeline.

The pipeline runs every step in order and records all step outputs. Each step receives the raw item and the outputs of all prior steps. The final extracted text is the last extracted output in pipeline order.

This lets you build explicit extraction policies while keeping every step outcome available for comparison and metrics.

For details, see the [`pipeline` extractor documentation](extractors/pipeline-utilities/pipeline.md).

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

python3 -m biblicus extract build --corpus corpora/extraction-demo \
  --step pass-through-text \
  --step pdf-text \
  --step metadata-text
```

The extracted text for the image comes from the `metadata-text` step because the image is not a text item.

## Example: selection within a pipeline

Selection is a pipeline step that chooses extracted text from previous pipeline steps. Selection is just another extractor in the pipeline, and it decides which prior output to carry forward.

```
python3 -m biblicus extract build --corpus corpora/extraction-demo \
  --step pass-through-text \
  --step metadata-text \
  --step select-text
```

The pipeline run produces one extraction run under `pipeline`. You can point retrieval backends at that run.

## Example: PDF with OCR fallback

Try text extraction first, fall back to OCR for scanned documents:

```
python3 -m biblicus extract build --corpus corpora/extraction-demo \
  --step pdf-text \
  --step ocr-rapidocr \
  --step select-text
```

This pipeline tries `pdf-text` first for PDFs with text layers, falls back to `ocr-rapidocr` for scanned PDFs, and uses `select-text` to pick the first successful result.

## Example: VLM for complex documents

Use vision-language models for documents with complex layouts:

```
python3 -m biblicus extract build --corpus corpora/extraction-demo \
  --step docling-granite
```

The `docling-granite` extractor uses IBM Research's Granite Docling-258M VLM for high-accuracy extraction of tables, code blocks, and equations.

## Inspecting and deleting extraction runs

Extraction runs are stored under the corpus and can be listed and inspected.

```
python3 -m biblicus extract list --corpus corpora/extraction-demo
python3 -m biblicus extract show --corpus corpora/extraction-demo --run pipeline:EXTRACTION_RUN_ID
```

Deletion is explicit and requires typing the exact run reference as confirmation:

```
python3 -m biblicus extract delete --corpus corpora/extraction-demo \
  --run pipeline:EXTRACTION_RUN_ID \
  --confirm pipeline:EXTRACTION_RUN_ID
```

## Use extracted text in retrieval

Retrieval backends can build and query using a selected extraction run. This is configured by passing `extraction_run=extractor_id:run_id` to the backend build command.

```
python3 -m biblicus build --corpus corpora/extraction-demo --backend sqlite-full-text-search \
  --config extraction_run=pipeline:EXTRACTION_RUN_ID
python3 -m biblicus query --corpus corpora/extraction-demo --query extracted
```

## What extraction is not

Text extraction does not mutate the raw corpus. It is derived output that can be regenerated and compared across implementations.

Optical character recognition and speech to text are implemented as extractors so you can compare providers and configurations while keeping raw items immutable.

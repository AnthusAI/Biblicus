# Text Extractors

Biblicus provides a plugin-based text extraction system supporting diverse document types, media formats, and processing strategies.

## Extractor Categories

### [Text & Document Processing](text-document/index.md)

Basic text extraction from structured documents and plain text formats.

- [**pass-through-text**](text-document/pass-through.md) - Returns existing extracted text without re-extraction
- [**metadata-text**](text-document/metadata.md) - Extracts text from item metadata (title, tags, etc.)
- [**pdf-text**](text-document/pdf.md) - Extracts text from PDF documents using pypdf
- [**markitdown**](text-document/markitdown.md) - Microsoft MarkItDown for Office documents and web content
- [**unstructured**](text-document/unstructured.md) - Unstructured.io for complex document parsing

### [Optical Character Recognition (OCR)](ocr/index.md)

Traditional OCR for extracting text from images and scanned documents.

- [**ocr-rapidocr**](ocr/rapidocr.md) - RapidOCR for fast ONNX-based text recognition
- [**ocr-paddleocr-vl**](ocr/paddleocr-vl.md) - PaddleOCR vision-language model for document understanding

### [Vision-Language Models (VLM)](vlm-document/index.md)

Advanced VLM-based document understanding with layout analysis and structured extraction.

- [**docling-smol**](vlm-document/docling-smol.md) - SmolDocling-256M for fast document processing
- [**docling-granite**](vlm-document/docling-granite.md) - Granite Docling-258M for high-accuracy extraction

### [Speech-to-Text (STT)](speech-to-text/index.md)

Audio transcription for spoken content in video and audio files.

- [**stt-openai**](speech-to-text/openai.md) - OpenAI Whisper API for audio transcription
- [**stt-deepgram**](speech-to-text/deepgram.md) - Deepgram Nova-2 for fast, accurate transcription

### [Pipeline Utilities](pipeline-utilities/index.md)

Meta-extractors for combining, selecting, and orchestrating extraction strategies.

- [**select-text**](pipeline-utilities/select-text.md) - Selects first successful extractor from a list
- [**select-longest-text**](pipeline-utilities/select-longest.md) - Selects longest output from multiple extractors
- [**select-override**](pipeline-utilities/select-override.md) - Overrides extraction for specific items by ID
- [**select-smart-override**](pipeline-utilities/select-smart-override.md) - Overrides extraction based on media type patterns
- [**pipeline**](pipeline-utilities/pipeline.md) - Chains multiple extractors sequentially

## Quick Start

### Installation

Most extractors require optional dependencies:

```bash
# Basic text extraction (included by default)
pip install biblicus

# OCR extractors
pip install biblicus[ocr]           # RapidOCR
pip install biblicus[paddleocr]     # PaddleOCR VL

# VLM document understanding
pip install biblicus[docling]       # Docling (Transformers backend)
pip install biblicus[docling-mlx]   # Docling (MLX backend for Apple Silicon)

# Speech-to-text
pip install biblicus[openai]        # OpenAI Whisper
pip install biblicus[deepgram]      # Deepgram Nova-2

# Document processing
pip install biblicus[markitdown]    # MarkItDown (Python 3.10+)
pip install biblicus[unstructured]  # Unstructured.io
```

### Basic Usage

#### Command Line

```bash
# Initialize corpus
biblicus init my-corpus

# Ingest documents
biblicus ingest my-corpus document.pdf

# Extract text with specific extractor
biblicus extract my-corpus --extractor pdf-text
```

#### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract text using an extractor
results = corpus.extract_text(extractor_id="pdf-text")
```

## Choosing an Extractor

### For PDF Documents

- **Simple PDFs with text layers**: Use [pdf-text](text-document/pdf.md) (fast, no dependencies)
- **Scanned PDFs or complex layouts**: Use [ocr-rapidocr](ocr/rapidocr.md) or VLM extractors
- **Tables, equations, complex structure**: Use [docling-granite](vlm-document/docling-granite.md)

### For Office Documents

- **DOCX, XLSX, PPTX**: Use [markitdown](text-document/markitdown.md) or [unstructured](text-document/unstructured.md)
- **Complex layouts or scanned documents**: Use VLM extractors

### For Images

- **Simple text recognition**: Use [ocr-rapidocr](ocr/rapidocr.md)
- **Complex documents in images**: Use [ocr-paddleocr-vl](ocr/paddleocr-vl.md) or VLM extractors

### For Audio/Video

- **High accuracy, cost-effective**: Use [stt-deepgram](speech-to-text/deepgram.md)
- **OpenAI ecosystem integration**: Use [stt-openai](speech-to-text/openai.md)

### For Multiple Strategies

- **Fallback chain**: Use [select-text](pipeline-utilities/select-text.md)
- **Best output selection**: Use [select-longest-text](pipeline-utilities/select-longest.md)
- **Per-item overrides**: Use [select-override](pipeline-utilities/select-override.md) or [select-smart-override](pipeline-utilities/select-smart-override.md)

## See Also

- [EXTRACTION.md](../EXTRACTION.md) - Extraction pipeline concepts and architecture
- [API Reference](../api.rst) - Python API documentation
- [README.md](../README.md) - Getting started guide

# OpenAI Whisper Speech-to-Text Extractor

**Extractor ID:** `stt-openai`

**Category:** [Speech-to-Text Extractors](index.md)

## Overview

The OpenAI speech-to-text extractor uses OpenAI's Whisper API to transcribe audio files. It provides high-quality transcription with support for multiple languages, timestamps, and hallucination suppression.

Whisper is a robust, production-ready speech recognition system trained on diverse audio data. The API provides reliable transcription without requiring local model management or GPU resources.

## Installation

Install the OpenAI Python client:

```bash
pip install "biblicus[openai]"
```

You'll also need an OpenAI API key.

## Supported Media Types

- `audio/mpeg` - MP3 audio
- `audio/mp4` - M4A audio
- `audio/wav` - WAV audio
- `audio/webm` - WebM audio
- `audio/flac` - FLAC audio
- `audio/ogg` - OGG audio
- `audio/*` - Any audio format supported by OpenAI

Only audio items are processed. Other media types are automatically skipped.

## Configuration

### Config Schema

```python
class OpenAiSpeechToTextExtractorConfig(BaseModel):
    model: str = "whisper-1"
    response_format: str = "json"
    language: Optional[str] = None
    prompt: Optional[str] = None
    no_speech_probability_threshold: Optional[float] = None
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `model` | str | `whisper-1` | OpenAI transcription model |
| `response_format` | str | `json` | Response format: `json`, `verbose_json`, `text`, `srt`, `vtt` |
| `language` | str or null | `null` | ISO-639-1 language code hint |
| `prompt` | str or null | `null` | Optional prompt to guide transcription style |
| `no_speech_probability_threshold` | float or null | `null` | Threshold to suppress hallucinations (requires `verbose_json`) |

### Response Formats

- **json** (default): Simple transcript text
- **verbose_json**: Includes segments, timestamps, and no-speech probabilities
- **text**: Plain text transcript
- **srt**: SubRip subtitle format
- **vtt**: WebVTT subtitle format

## Usage

### Command Line

#### Basic Usage

```bash
# Configure API key
export OPENAI_API_KEY="your-key-here"

# Extract audio transcripts
biblicus extract my-corpus --extractor stt-openai
```

#### Custom Configuration

```bash
# Transcribe with language hint
biblicus extract my-corpus --extractor stt-openai \
  --config language=es

# Use verbose format with hallucination suppression
biblicus extract my-corpus --extractor stt-openai \
  --config response_format=verbose_json \
  --config no_speech_probability_threshold=0.6
```

#### Recipe File

```yaml
extractor_id: stt-openai
config:
  model: whisper-1
  response_format: json
  language: en
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract with defaults
results = corpus.extract_text(extractor_id="stt-openai")

# Extract with language hint
results = corpus.extract_text(
    extractor_id="stt-openai",
    config={"language": "es"}
)

# Extract with hallucination suppression
results = corpus.extract_text(
    extractor_id="stt-openai",
    config={
        "response_format": "verbose_json",
        "no_speech_probability_threshold": 0.6
    }
)
```

### In Pipeline

#### Audio Fallback

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: stt-openai
    - extractor_id: select-text
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "audio/.*"
      extractor: stt-openai
```

## Examples

### Podcast Transcription

Transcribe podcast episodes:

```bash
export OPENAI_API_KEY="your-key"
biblicus extract podcasts --extractor stt-openai
```

### Multilingual Audio

Transcribe audio in multiple languages:

```bash
# Spanish audio
biblicus extract spanish-audio --extractor stt-openai \
  --config language=es

# French audio
biblicus extract french-audio --extractor stt-openai \
  --config language=fr
```

### Interview Transcription

Transcribe interviews with custom prompt:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("interviews")

results = corpus.extract_text(
    extractor_id="stt-openai",
    config={
        "prompt": "This is an interview with industry experts discussing technology."
    }
)
```

### Hallucination Suppression

Suppress hallucinated transcripts for silent audio:

```bash
biblicus extract audio-clips --extractor stt-openai \
  --config response_format=verbose_json \
  --config no_speech_probability_threshold=0.6
```

## API Configuration

### Environment Variable

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### User Config File

Add to `~/.biblicus/config.yml`:

```yaml
openai:
  api_key: YOUR_API_KEY_HERE
```

### Local Config File

Add to `.biblicus/config.yml` in your project:

```yaml
openai:
  api_key: YOUR_API_KEY_HERE
```

## Language Support

Whisper supports 50+ languages including:

- English (`en`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)
- Italian (`it`)
- Portuguese (`pt`)
- Dutch (`nl`)
- Russian (`ru`)
- Chinese (`zh`)
- Japanese (`ja`)
- Korean (`ko`)
- Arabic (`ar`)

And many more. See OpenAI documentation for the full list.

## Performance

- **Speed**: ~0.1x realtime (10-minute audio in ~1 minute)
- **Accuracy**: Excellent (state-of-the-art for many languages)
- **Cost**: Per-minute API pricing (check OpenAI pricing)

## Error Handling

### Missing Dependency

If OpenAI client is not installed:

```
ExtractionRunFatalError: OpenAI speech to text extractor requires an optional dependency.
Install it with pip install "biblicus[openai]".
```

### Missing API Key

If API key is not configured:

```
ExtractionRunFatalError: OpenAI speech to text extractor requires an OpenAI API key.
Set OPENAI_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under openai.api_key.
```

### Non-Audio Items

Non-audio items are silently skipped (returns `None`).

### API Errors

API errors (rate limits, invalid audio, etc.) are recorded as per-item errors but don't halt extraction.

## Hallucination Suppression

Whisper may generate "hallucinated" transcripts for silent or noise-only audio. Use `no_speech_probability_threshold` to suppress these:

```yaml
config:
  response_format: verbose_json
  no_speech_probability_threshold: 0.6
```

This requires `verbose_json` format which includes per-segment no-speech probabilities. If any segment exceeds the threshold, the entire transcript is suppressed (empty output).

### Recommended Threshold

- **0.5-0.6**: Conservative (suppress likely hallucinations)
- **0.7-0.8**: Moderate (suppress obvious hallucinations)
- **0.9+**: Aggressive (only keep very confident speech)

## Prompt Guidance

The optional `prompt` parameter guides transcription style:

```yaml
config:
  prompt: "This is a technical podcast about machine learning and AI."
```

Prompts can:
- Provide context about the audio
- Specify terminology or proper nouns
- Guide formatting preferences
- Improve accuracy for domain-specific content

## Use Cases

### Podcast Archives

Transcribe podcast episodes for search:

```bash
biblicus extract podcasts --extractor stt-openai
```

### Meeting Recordings

Create searchable meeting transcripts:

```bash
biblicus extract meetings --extractor stt-openai
```

### Lecture Capture

Transcribe educational content:

```bash
biblicus extract lectures --extractor stt-openai \
  --config language=en
```

### Multilingual Content

Process audio in multiple languages:

```python
from biblicus import Corpus

# Let Whisper auto-detect language
corpus = Corpus.from_directory("multilingual-audio")
results = corpus.extract_text(extractor_id="stt-openai")
```

## When to Use OpenAI vs Deepgram

### Use OpenAI Whisper when:
- You need excellent multilingual support
- Audio quality varies
- You want state-of-the-art accuracy
- Cost is acceptable

### Use Deepgram when:
- You need faster processing
- Speaker diarization is required
- Real-time transcription is needed
- Lower word error rate for English

### Comparison

| Feature | OpenAI Whisper | Deepgram |
|---------|---------------|----------|
| Languages | 50+ | 30+ |
| Speed | Moderate | Fast |
| Accuracy | Excellent | Excellent |
| Diarization | No | Yes |
| Formatting | Basic | Advanced |

## Best Practices

### Provide Language Hints

When you know the language, specify it:

```yaml
config:
  language: es  # Spanish
```

### Use Prompts for Context

Guide transcription with relevant context:

```yaml
config:
  prompt: "Interview with Dr. Smith about quantum computing."
```

### Monitor API Usage

Track API costs and usage:

```python
# Check number of items processed
print(f"Processed items: {results.stats.processed_items}")
```

### Suppress Hallucinations

For mixed content (speech + silence), enable suppression:

```yaml
config:
  response_format: verbose_json
  no_speech_probability_threshold: 0.6
```

## Related Extractors

### Same Category

- [stt-deepgram](deepgram.md) - Deepgram speech-to-text

### Alternatives

- [stt-deepgram](deepgram.md) - Faster, includes diarization
- [pass-through-text](../text-document/pass-through.md) - Direct text files
- [metadata-text](../text-document/metadata.md) - Metadata-based text

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Choose longest output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Media type routing
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Speech-to-Text Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [User Configuration](../../USER_CONFIGURATION.md)
- [OpenAI Whisper API Documentation](https://platform.openai.com/docs/guides/speech-to-text)

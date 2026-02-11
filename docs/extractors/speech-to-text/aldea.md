# Aldea Speech-to-Text Extractor

**Extractor ID:** `stt-aldea`

**Category:** [Speech-to-Text Extractors](index.md)

## Overview

The Aldea speech-to-text extractor uses the [Aldea Speech-to-Text API](https://platform.aldea.ai/docs) to transcribe audio files. The API supports pre-recorded audio via REST and returns Deepgram-compatible response shapes (channels, alternatives, transcript). You can use the optional [deepgram-transform](deepgram-transform.md) stage after `stt-aldea` to render words or utterances when timestamps or diarization are enabled.

## Installation

Install the optional Aldea dependency (httpx):

```bash
pip install "biblicus[aldea]"
```

You'll also need an Aldea API key (tokens start with `org_`).

## Supported Media Types

- `audio/mpeg` - MP3 audio
- `audio/mp4` - M4A audio
- `audio/wav` - WAV audio
- `audio/webm` - WebM audio
- `audio/flac` - FLAC audio
- `audio/ogg` - OGG audio
- `audio/*` - Any audio format supported by Aldea (MP3, AAC, FLAC, WAV, OGG, WebM, Opus, M4A; max duration defaults to 10 minutes)

Only audio items are processed. Other media types are automatically skipped.

## Configuration

### Config Schema

```python
class AldeaSpeechToTextExtractorConfig(BaseModel):
    language: Optional[str] = None   # BCP-47 (e.g. en-US, es)
    diarization: bool = False
    timestamps: bool = False
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `language` | str or null | `null` | Language code hint in BCP-47 format (e.g. `en-US`, `es`) |
| `diarization` | bool | `false` | Enable speaker diarization (requires word timestamps) |
| `timestamps` | bool | `false` | Include per-word timestamps in the response |

## Usage

### Command Line

#### Basic Usage

```bash
# Configure API key
export ALDEA_API_KEY="your-key-here"

# Extract audio transcripts
biblicus extract my-corpus --extractor stt-aldea
```

#### Custom Configuration

```bash
# Enable language hint and timestamps
biblicus extract my-corpus --extractor stt-aldea \
  --config language=en-US,timestamps=true

# Enable speaker diarization
biblicus extract my-corpus --extractor stt-aldea \
  --config diarization=true
```

#### Configuration File

```yaml
extractor_id: stt-aldea
config:
  language: null
  diarization: false
  timestamps: false
```

```bash
biblicus extract my-corpus --configuration configuration.yml
```

### Python API

```python
from biblicus import Corpus
from biblicus.extractors import get_extractor

corpus = Corpus.from_directory("my-corpus")
extractor = get_extractor("stt-aldea")
config = extractor.validate_config({})
# Then use in your extraction pipeline
```

## Authentication

Set your Aldea API key via environment or user config. Environment takes precedence.

### Environment Variable

```bash
export ALDEA_API_KEY="org_your_api_key_here"
```

### Configuration File

Add to `~/.biblicus/config.yml` or `./.biblicus/config.yml`:

```yaml
aldea:
  api_key: org_your_api_key_here
```

See [User configuration](../../user-configuration.md) for details.

## Response and Metadata

The extractor stores the full Aldea API response in stage metadata under the key `aldea`. The structure matches the [Pre-Recorded Audio API](https://platform.aldea.ai/docs/stt-api-reference/pre-recorded-audio): `metadata` (request_id, duration, channels) and `results.channels[].alternatives[].transcript` (and optionally `words` when timestamps are enabled). You can use [deepgram-transform](deepgram-transform.md) in a pipeline after `stt-aldea` to render words or utterances from this metadata.

## Error Handling

- **Missing optional dependency**: Install with `pip install "biblicus[aldea]"`.
- **Missing API key**: Set `ALDEA_API_KEY` or configure `aldea.api_key` in user config.
- **HTTP errors**: The extractor calls `response.raise_for_status()`; non-2xx responses surface as exceptions.

## See Also

- [Aldea STT API Documentation](https://platform.aldea.ai/docs)
- [Pre-Recorded Audio API Reference](https://platform.aldea.ai/docs/stt-api-reference/pre-recorded-audio)
- [Authentication](https://platform.aldea.ai/docs/authentication)
- [stt-deepgram](deepgram.md) - Deepgram Nova-3 extractor
- [stt-openai](openai.md) - OpenAI Whisper extractor
- [deepgram-transform](deepgram-transform.md) - Render Deepgram-shaped metadata (e.g. from Aldea) into text

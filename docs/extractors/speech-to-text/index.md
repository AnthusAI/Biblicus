# Speech-to-Text (STT)

Audio transcription extractors for converting spoken content into text.

## Overview

Speech-to-text extractors transcribe audio from video and audio files. They are ideal for:

- Podcast transcription
- Lecture and presentation recordings
- Interview transcripts
- Video content with narration
- Audio messages and recordings

The raw audio bytes remain unchanged in the corpus; only transcribed text is stored in extraction results.

## Available Extractors

### [stt-openai](openai.md)

OpenAI Whisper API for audio transcription:

- **Model**: Whisper-1 (OpenAI hosted)
- **Accuracy**: Excellent general-purpose accuracy
- **Languages**: 50+ languages supported
- **Features**: Automatic language detection, translation
- **Formats**: MP3, MP4, MPEG, MPGA, M4A, WAV, WEBM

**Installation**: `pip install biblicus[openai]`

**Best for**: General transcription, multi-language content, OpenAI ecosystem integration

### [stt-deepgram](deepgram.md)

Deepgram Nova-3 for fast, accurate transcription:

- **Model**: Nova-3 (default), Nova-2, other Deepgram models
- **Accuracy**: Lower word error rate than Whisper
- **Features**: Smart formatting, speaker diarization, filler word filtering
- **Languages**: 30+ languages supported
- **Formats**: Most audio formats

**Installation**: `pip install biblicus[deepgram]`

**Best for**: High-accuracy transcription, speaker diarization, professional content

## Choosing an Extractor

| Use Case | Recommended | Notes |
|----------|-------------|-------|
| General transcription | [stt-deepgram](deepgram.md) | Better accuracy, formatting |
| Multi-language content | [stt-openai](openai.md) | More languages supported |
| Speaker identification | [stt-deepgram](deepgram.md) | Has diarization feature |
| Translation to English | [stt-openai](openai.md) | Built-in translation |
| Cost-sensitive | [stt-deepgram](deepgram.md) | Competitive pricing |
| OpenAI workflow | [stt-openai](openai.md) | Single API key |

## Performance Comparison

### OpenAI Whisper

- **Accuracy**: Excellent (WER ~5-10%)
- **Speed**: Moderate
- **Languages**: 50+
- **Max file size**: 25 MB
- **Pricing**: $0.006/minute

### Deepgram Nova-3

- **Accuracy**: Superior (WER ~3-7%)
- **Speed**: Fast (real-time capable)
- **Languages**: 30+
- **Max file size**: No limit
- **Pricing**: Competitive (volume discounts)

## Common Patterns

### Fallback Chain

Try Deepgram first, fall back to OpenAI:

```yaml
extractor_id: select-text
config:
  extractors:
    - stt-deepgram
    - stt-openai
```

### Language-Specific Routing

Route by media type or use overrides:

```yaml
extractor_id: select-smart-override
config:
  default_extractor: stt-deepgram
  overrides:
    - media_type_pattern: "audio/.*"
      extractor: stt-deepgram
    - media_type_pattern: "video/.*"
      extractor: stt-openai
```

### Speaker Diarization

Use Deepgram with diarization enabled:

```yaml
extractor_id: stt-deepgram
config:
  diarize: true
  smart_format: true
```

## Authentication

Both extractors require API keys:

### Environment Variables

```bash
export OPENAI_API_KEY="your-openai-key"
export DEEPGRAM_API_KEY="your-deepgram-key"
```

### Configuration File

Add to `~/.biblicus/config.yml`:

```yaml
openai:
  api_key: YOUR_OPENAI_KEY

deepgram:
  api_key: YOUR_DEEPGRAM_KEY
```

## Supported Audio Formats

Both extractors support common audio formats:

- MP3
- MP4 (audio track)
- MPEG
- MPGA
- M4A
- WAV
- WEBM
- OGG
- FLAC

## See Also

- [Extractors Overview](../index.md)
- [stt-openai](openai.md) - OpenAI Whisper extractor details
- [stt-deepgram](deepgram.md) - Deepgram Nova-3 extractor details
- [Pipeline Utilities](../pipeline-utilities/index.md) - Combining extraction strategies

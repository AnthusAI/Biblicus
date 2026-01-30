# Deepgram Speech-to-Text Extractor

**Extractor ID:** `stt-deepgram`

**Category:** [Speech-to-Text Extractors](index.md)

## Overview

The Deepgram speech-to-text extractor uses Deepgram's neural network-based API to transcribe audio files. It provides fast, accurate transcription with advanced features like speaker diarization, smart formatting, and lower word error rates than traditional ASR systems.

Deepgram's Nova-3 model delivers state-of-the-art accuracy with excellent performance on diverse audio conditions. The API is optimized for speed and scale, making it ideal for large corpus processing.

## Installation

Install the Deepgram Python SDK:

```bash
pip install "biblicus[deepgram]"
```

You'll also need a Deepgram API key.

## Supported Media Types

- `audio/mpeg` - MP3 audio
- `audio/mp4` - M4A audio
- `audio/wav` - WAV audio
- `audio/webm` - WebM audio
- `audio/flac` - FLAC audio
- `audio/ogg` - OGG audio
- `audio/*` - Any audio format supported by Deepgram

Only audio items are processed. Other media types are automatically skipped.

## Configuration

### Config Schema

```python
class DeepgramSpeechToTextExtractorConfig(BaseModel):
    model: str = "nova-3"
    language: Optional[str] = None
    punctuate: bool = True
    smart_format: bool = True
    diarize: bool = False
    filler_words: bool = False
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `model` | str | `nova-3` | Deepgram model: `nova-3`, `nova-2`, `base`, `enhanced` |
| `language` | str or null | `null` | Language code hint (e.g., `en`, `es`, `fr`) |
| `punctuate` | bool | `true` | Add punctuation to transcript |
| `smart_format` | bool | `true` | Apply smart formatting (numbers, dates, etc.) |
| `diarize` | bool | `false` | Enable speaker diarization |
| `filler_words` | bool | `false` | Include filler words (um, uh, etc.) |

### Model Options

- **nova-3** (default): Latest model, best accuracy, lowest WER
- **nova-2**: Previous generation, good accuracy
- **base**: Basic model, faster, lower accuracy
- **enhanced**: Enhanced accuracy for challenging audio

## Usage

### Command Line

#### Basic Usage

```bash
# Configure API key
export DEEPGRAM_API_KEY="your-key-here"

# Extract audio transcripts
biblicus extract my-corpus --extractor stt-deepgram
```

#### Custom Configuration

```bash
# Enable speaker diarization
biblicus extract my-corpus --extractor stt-deepgram \
  --config diarize=true

# Transcribe Spanish audio
biblicus extract my-corpus --extractor stt-deepgram \
  --config language=es

# Disable smart formatting
biblicus extract my-corpus --extractor stt-deepgram \
  --config smart_format=false
```

#### Recipe File

```yaml
extractor_id: stt-deepgram
config:
  model: nova-3
  punctuate: true
  smart_format: true
  diarize: false
  filler_words: false
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
results = corpus.extract_text(extractor_id="stt-deepgram")

# Extract with speaker diarization
results = corpus.extract_text(
    extractor_id="stt-deepgram",
    config={"diarize": True}
)

# Extract with language hint
results = corpus.extract_text(
    extractor_id="stt-deepgram",
    config={
        "language": "es",
        "model": "nova-3"
    }
)
```

### In Pipeline

#### Audio Processing

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: stt-deepgram
    - extractor_id: select-text
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "audio/.*"
      extractor: stt-deepgram
```

## Examples

### Podcast Transcription

Transcribe podcast episodes with smart formatting:

```bash
export DEEPGRAM_API_KEY="your-key"
biblicus extract podcasts --extractor stt-deepgram \
  --config smart_format=true
```

### Multi-Speaker Audio

Enable speaker diarization for interviews or meetings:

```bash
biblicus extract meetings --extractor stt-deepgram \
  --config diarize=true
```

### Multilingual Content

Transcribe Spanish audio:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("spanish-audio")

results = corpus.extract_text(
    extractor_id="stt-deepgram",
    config={"language": "es"}
)
```

### Include Filler Words

Preserve filler words for linguistic analysis:

```bash
biblicus extract interviews --extractor stt-deepgram \
  --config filler_words=true
```

## API Configuration

### Environment Variable

```bash
export DEEPGRAM_API_KEY="your-api-key-here"
```

### User Config File

Add to `~/.biblicus/config.yml`:

```yaml
deepgram:
  api_key: YOUR_API_KEY_HERE
```

### Local Config File

Add to `.biblicus/config.yml` in your project:

```yaml
deepgram:
  api_key: YOUR_API_KEY_HERE
```

## Language Support

Deepgram supports 30+ languages including:

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
- Hindi (`hi`)

And many more. See Deepgram documentation for the full list.

## Smart Formatting

With `smart_format: true`, Deepgram automatically formats:

- **Numbers**: "one hundred" → "100"
- **Dates**: "january first" → "January 1st"
- **Times**: "three thirty pm" → "3:30 PM"
- **Currency**: "fifty dollars" → "$50"
- **Addresses**: Street numbers and names
- **Phone numbers**: Digit sequences

Example:

```
Input audio: "Call me at five five five one two three four"
Output: "Call me at 555-1234"
```

## Speaker Diarization

With `diarize: true`, Deepgram identifies different speakers:

```
Speaker 0: Hello, how are you?
Speaker 1: I'm doing well, thanks for asking.
Speaker 0: Great to hear!
```

Note: Deepgram's transcription API returns speaker labels in the detailed response. The Biblicus extractor combines all speaker segments into a single transcript.

## Performance

- **Speed**: Fast (~0.05x realtime for Nova-3)
- **Accuracy**: Excellent (lower WER than Whisper for English)
- **Word Error Rate**: ~8-10% for Nova-3 on clean audio
- **Cost**: Per-minute API pricing (check Deepgram pricing)

## Error Handling

### Missing Dependency

If Deepgram SDK is not installed:

```
ExtractionRunFatalError: Deepgram speech to text extractor requires an optional dependency.
Install it with pip install "biblicus[deepgram]".
```

### Missing API Key

If API key is not configured:

```
ExtractionRunFatalError: Deepgram speech to text extractor requires a Deepgram API key.
Set DEEPGRAM_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under deepgram.api_key.
```

### Non-Audio Items

Non-audio items are silently skipped (returns `None`).

### API Errors

API errors (rate limits, invalid audio, etc.) are recorded as per-item errors but don't halt extraction.

## Use Cases

### Podcast Archives

Transcribe podcast episodes for search:

```bash
biblicus extract podcasts --extractor stt-deepgram \
  --config smart_format=true
```

### Meeting Recordings

Create searchable meeting transcripts with speaker identification:

```bash
biblicus extract meetings --extractor stt-deepgram \
  --config diarize=true
```

### Call Center Audio

Process customer service calls:

```bash
biblicus extract calls --extractor stt-deepgram \
  --config model=nova-3 \
  --config diarize=true
```

### Lecture Capture

Transcribe educational content with smart formatting:

```bash
biblicus extract lectures --extractor stt-deepgram \
  --config smart_format=true \
  --config punctuate=true
```

## When to Use Deepgram vs OpenAI

### Use Deepgram when:
- You need fastest processing speed
- Speaker diarization is required
- Lower word error rate for English is critical
- Smart formatting is desired
- Processing large volumes

### Use OpenAI Whisper when:
- You need broader language support
- Audio quality varies significantly
- You prefer OpenAI ecosystem
- Multilingual content is diverse

### Comparison

| Feature | Deepgram | OpenAI Whisper |
|---------|----------|----------------|
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| English WER | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Languages | 30+ | 50+ |
| Diarization | ✅ | ❌ |
| Smart Formatting | ✅ | ❌ |
| Filler Words | ✅ | ❌ |

## Best Practices

### Use Nova-3 for Best Results

Nova-3 provides the lowest word error rate:

```yaml
config:
  model: nova-3
```

### Enable Smart Formatting

Make transcripts more readable:

```yaml
config:
  smart_format: true
  punctuate: true
```

### Use Diarization for Multi-Speaker Audio

Identify speakers in meetings and interviews:

```yaml
config:
  diarize: true
```

### Provide Language Hints

When you know the language, specify it:

```yaml
config:
  language: en
```

### Monitor API Usage

Track API costs:

```python
print(f"Processed items: {results.stats.processed_items}")
```

## Advanced Features

### Filler Words

Include or exclude filler words:

```yaml
config:
  filler_words: true  # Include "um", "uh", etc.
```

### Custom Model Selection

Choose model based on needs:

```yaml
# Best accuracy
config:
  model: nova-3

# Faster processing
config:
  model: base
```

## Related Extractors

### Same Category

- [stt-openai](openai.md) - OpenAI Whisper speech-to-text

### Alternatives

- [stt-openai](openai.md) - More languages, different accuracy profile
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
- [Deepgram API Documentation](https://developers.deepgram.com/)

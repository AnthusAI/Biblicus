# Deepgram Transform Extractor

**Extractor ID:** `deepgram-transform`

**Category:** [Speech-to-Text](index.md)

## Overview

The Deepgram transform extractor renders text from the structured metadata produced by
`stt-deepgram`. Use it when you want to choose a specific Deepgram representation
(`transcript`, `utterances`, or `words`) or filter by channel or speaker.

This extractor does not call Deepgram. It only transforms metadata from a prior pipeline stage.

## Installation

No additional dependencies required. The transform runs on existing Deepgram metadata.

## Configuration

```python
class DeepgramTranscriptTransformConfig(BaseModel):
    source: str = "transcript"  # transcript | utterances | words
    channels: Optional[List[int]] = None
    speakers: Optional[List[int]] = None
    join_with: str = " "
    include_channel_labels: bool = False
    include_speaker_labels: bool = False
```

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `source` | str | ✅ | `transcript`, `utterances`, or `words` |
| `channels` | list[int] | ❌ | Channel indices to include (default: all) |
| `speakers` | list[int] | ❌ | Speaker indices to include (default: all) |
| `join_with` | str | ❌ | Separator when joining utterances or words |
| `include_channel_labels` | bool | ❌ | Prefix output with `[channel_n]` |
| `include_speaker_labels` | bool | ❌ | Prefix output with `[speaker_n]` |

## Usage

### Pipeline Example

```yaml
extractor_id: pipeline
config:
  stages:
    - extractor_id: stt-deepgram
      config:
        diarize: true
    - extractor_id: deepgram-transform
      config:
        source: utterances
        speakers: [0]
```

### Command Line

```bash
biblicus extract build --corpus corpora/Alfa \
  --stage "stt-deepgram:diarize=true" \
  --stage "deepgram-transform:source=utterances,speakers=[0]"
```

## Notes

- `deepgram-transform` requires a prior stage that provides Deepgram metadata, typically
  `stt-deepgram`.
- When `source=words`, the extractor joins word entries with `join_with`.
- When `source=utterances`, each utterance transcript is joined with `join_with`.

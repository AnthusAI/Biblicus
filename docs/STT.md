# Speech to text extraction

Speech to text extractors transcribe audio items into text artifacts. The raw audio bytes remain unchanged in the corpus.

## Available providers

Biblicus supports multiple speech to text providers. Each is an optional dependency.

## stt-openai

Speech to text using OpenAI Whisper.

- Backed by the optional `openai` dependency
- Requires an OpenAI API key

To install:

```
python -m pip install "biblicus[openai]"
```

To configure, set `OPENAI_API_KEY` or add to `~/.biblicus/config.yml`:

```yaml
openai:
  api_key: YOUR_KEY_HERE
```

Configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `whisper-1` | OpenAI transcription model |
| `response_format` | `json` | Response format (json, verbose_json, text, srt, vtt) |
| `language` | None | Language hint |
| `prompt` | None | Prompt to guide transcription |

Example:

```
python -m biblicus extract build --corpus corpora/demo \
  --stage 'stt-openai:model=whisper-1,language=en'
```

## stt-deepgram

Speech to text using Deepgram.

- Backed by the optional `deepgram-sdk` dependency
- Requires a Deepgram API key
- Default model is nova-3 with smart formatting enabled

To install:

```
python -m pip install "biblicus[deepgram]"
```

To configure, set `DEEPGRAM_API_KEY` or add to `~/.biblicus/config.yml`:

```yaml
deepgram:
  api_key: YOUR_KEY_HERE
```

Configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `nova-3` | Deepgram model (nova-3, nova-2, etc.) |
| `language` | None | Language code hint |
| `punctuate` | `true` | Add punctuation |
| `smart_format` | `true` | Apply smart formatting |
| `diarize` | `false` | Enable speaker diarization |
| `filler_words` | `false` | Include filler words |

Example:

```
python -m biblicus extract build --corpus corpora/demo \
  --stage 'stt-deepgram:model=nova-3,language=en'
```

## stt-aldea

Speech to text using the Aldea API.

- Backed by the optional `aldea` dependency (httpx)
- Requires an Aldea API key
- Response shape is Deepgram-compatible (channels, alternatives, transcript)

To install:

```
python -m pip install "biblicus[aldea]"
```

To configure, set `ALDEA_API_KEY` or add to `~/.biblicus/config.yml`:

```yaml
aldea:
  api_key: org_YOUR_KEY_HERE
```

Configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `language` | None | Language code (BCP-47, e.g. en-US, es) |
| `diarization` | `false` | Enable speaker diarization |
| `timestamps` | `false` | Include per-word timestamps |

Example:

```
python -m biblicus extract build --corpus corpora/demo \
  --stage 'stt-aldea:language=en-US'
```

## Choosing a provider

All three providers transcribe audio items. Choose based on your needs:

- **OpenAI Whisper**: Well-known, widely used, good accuracy
- **Deepgram**: Lower word error rate with nova-3, more configuration options, speaker diarization
- **Aldea**: Aldea-hosted API with Deepgram-compatible response shape; use with `biblicus[aldea]`

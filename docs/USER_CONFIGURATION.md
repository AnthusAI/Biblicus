# User configuration

Biblicus supports a small user configuration file for optional integrations.

This is separate from corpus configuration. A corpus is a folder you can copy and share. User configuration usually contains machine-specific settings such as credentials.

## Where it looks

Biblicus looks for user configuration in two places, in this order.

1. `~/.biblicus/config.yml`
2. `./.biblicus/config.yml`

If both files exist, the local configuration overrides the home configuration.

## File format

The configuration file is YAML and is parsed using the `dotyaml` approach (YAML with optional environment variable interpolation).

## Example: OpenAI speech to text

Create a config file with an OpenAI API key.

You can start from the included example configuration file:

- Copy `.biblicus/config.example.yml` to `~/.biblicus/config.yml`, or
- Copy `.biblicus/config.example.yml` to `./.biblicus/config.yml`

`~/.biblicus/config.yml`:

```yaml
openai:
  api_key: YOUR_KEY_HERE
```

The OpenAI speech to text extractor also supports the `OPENAI_API_KEY` environment variable. Environment takes precedence over configuration.

## Example: Deepgram speech to text

Create a config file with a Deepgram API key.

`~/.biblicus/config.yml`:

```yaml
deepgram:
  api_key: YOUR_KEY_HERE
```

The Deepgram speech to text extractor also supports the `DEEPGRAM_API_KEY` environment variable. Environment takes precedence over configuration.

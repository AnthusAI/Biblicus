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

## Reproducibility notes

User configuration is machine-specific. Do not bake secrets into corpora or datasets, and avoid storing user config
files in source control.

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

## Example: Aldea speech to text

Create a config file with an Aldea API key.

`~/.biblicus/config.yml`:

```yaml
aldea:
  api_key: YOUR_KEY_HERE
```

The Aldea speech to text extractor also supports the `ALDEA_API_KEY` environment variable. Environment takes precedence over configuration.

## Example: Neo4j graph extraction

Graph extraction uses a Neo4j backend. Biblicus can auto-start a local Neo4j Docker container if it is not already running.

Install the Neo4j Python driver before running graph extraction:

```
python -m pip install neo4j
```

If you use NLP-based graph extractors (for example `ner-entities` or `dependency-relations`), install the NLP model
package and the model data your configuration references.

`~/.biblicus/config.yml`:

```yaml
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: testpassword
  auto_start: true
  container_name: biblicus-neo4j
  docker_image: neo4j:5
  http_port: 7474
  bolt_port: 7687
```

Environment variables override configuration when present:

- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`
- `BIBLICUS_NEO4J_AUTO_START`
- `BIBLICUS_NEO4J_CONTAINER_NAME`
- `BIBLICUS_NEO4J_IMAGE`
- `BIBLICUS_NEO4J_HTTP_PORT`
- `BIBLICUS_NEO4J_BOLT_PORT`

## Common pitfalls

- Saving secrets in the corpus directory instead of a user config file.
- Forgetting that local configuration overrides home configuration.
- Expecting user configuration to be copied with a corpus.

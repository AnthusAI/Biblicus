# Use Cases

These tutorials are the fastest way to understand what Biblicus does: each one is a runnable
script that produces concrete artifacts (evidence, context, or transformed text), and each one is
covered by behavior specs so we can keep the tutorials honest over time.

```{toctree}
:maxdepth: 1
:caption: Tutorials

use_cases/notes_to_context_pack
use_cases/text_folder_search
use_cases/text_redact
```

```{toctree}
:maxdepth: 1
:caption: Advanced tutorials

use_cases/sequence_markov
```

## How to run the tutorials

All scripts assume you are running from the repository root with an editable install:

```bash
python -m pip install -e ".[dev]"
```

Each tutorial script accepts:

- `--corpus <path>`: where to create or reuse the managed folder for the tutorial (called a *corpus* in the docs)
- `--force`: purge that folder before running the tutorial

Some tutorials can run in both mock mode and real API mode. When a tutorial requires external
services, its integration behavior is also covered by `@integration` behavior specs.

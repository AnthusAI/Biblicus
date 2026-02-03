# Sequence Graph With Markov Analysis

Some text is more than a bag of sentences. It has a *shape*.

If you have ordered text where the sequence matters (chat transcripts, message threads, meeting
notes, or long-form documents with recurring phases), Markov analysis can learn a directed,
weighted transition graph that shows which “states” tend to follow which others.

This tutorial runs a complete loop on a bundled set of conversation-style texts:

1. Ingest text files into a managed folder on disk.
2. Build an extraction snapshot (pass-through for already-text items).
3. Run Markov analysis with topic-driven observations.
4. Export a GraphViz transition graph and supporting artifacts.

## Run it

This tutorial uses optional dependencies and (by default) an LLM call for state naming.

If you are running from a fresh clone, install the development dependencies and topic modeling
extras:

```bash
python -m pip install -e ".[dev,topic-modeling]"
```

```bash
python scripts/use_cases/sequence_markov_demo.py \
  --corpus corpora/tutorial_sequence_markov \
  --force
```

If you want state naming, set an API key in your environment (or in your Biblicus configuration
file):

```bash
export OPENAI_API_KEY="..."
```

If you want to run without state naming (for example, while debugging locally), disable it
explicitly:

```bash
python scripts/use_cases/sequence_markov_demo.py \
  --corpus corpora/tutorial_sequence_markov \
  --force \
  --config report.state_naming.enabled=false
```

## What you should see

The script prints a JSON object to standard output with:

- the extraction snapshot id it created
- the Markov analysis snapshot id
- paths to the generated artifacts

The most useful artifact to open first is the GraphViz file:

```json
{
  "transitions_dot_path": ".../corpora/tutorial_sequence_markov/.biblicus/runs/analysis/markov/<snapshot_id>/transitions.dot"
}
```

## How to interpret the output

Markov analysis writes a snapshot directory under the managed folder:

- `segments.jsonl`: the ordered segments for each item
- `observations.jsonl`: the observation record per segment
- `topic_modeling.json` and `topic_assignments.jsonl`: topic stage debugging artifacts
- `transitions.json`: the learned state transition matrix
- `transitions.dot`: a GraphViz visualization of the transition graph

The visualization is meant to be evidence-first:

- nodes are states inferred by the model
- edges are directed transitions, with weights derived from observed transitions in decoded paths

For deeper detail (including configurations, segmentation choices, and artifacts), see
`docs/MARKOV_ANALYSIS.md`.

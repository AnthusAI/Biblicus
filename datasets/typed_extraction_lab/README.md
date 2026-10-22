# Typed extraction lab

Evaluation set for the typed entity and relation extractor exploration (Kanbus story blbs-e14d5c).

| File | Content |
| --- | --- |
| `documents.jsonl` | 142 public documents: for each of the 71 published Shipped items (https://shipped.anth.us) the headline plus deck (`<n>h`) and the first body paragraph (`<n>b`). `n` is the item's index in slug order. |
| `vocabulary.yml` | The closed vocabulary: 9 entity kinds and 6 relation types, with the short label given to zero-shot extractors. Per-publication data, never hard-coded in Biblicus. |
| `annotations.txt` | The hand-written annotations (compact format below). |
| `gold.jsonl` | Gold labels generated from `annotations.txt`: mention spans (character offsets, kind, canonical key) and relations (canonical subject key, type, object key). |

## Provenance and honesty

The gold set was annotated by an AI agent (Claude Sonnet 5.5) acting as a human proxy, seeded from the
editor-entered front-matter entities (`maker` and `task`) of each item and extended by reading every document.
It has not been reviewed by a human editor. A spot check of 12 randomly chosen documents and a consistency pass
(every surface form annotated in two or more documents was checked for omissions elsewhere) found 25 omitted mentions
(added) and 2 inconsistent `reasoning` task mentions (removed). Expect residual noise in the fuzzy kinds (`task`, `concept`, `technique`); the per-kind scores
in the evaluation report should be read with that in mind. All text is public; the set contains no email addresses.

## Annotation rules

- `maker`: organisation or person that releases or trains a model, including base-model makers when named.
- `model`: a specific named model or checkpoint (size or version suffix), including hosted model products.
- `model_family`: a named series without a size suffix (for example `Gemma 4`).
- `task`: a job a model is built for (`voice cloning`, `text-to-speech`, `content moderation`); a surface variant resolves to the editor's name (`TTS` to `text-to-speech`).
- `technique`: a training or architecture method (`LoRA`, `mixture-of-experts`, `reinforcement learning`).
- `licence`: a named licence, including maker-specific ones; the span is the licence name only.
- `dataset`: a named benchmark, test set or training dataset.
- `platform`: a named service, runtime or hub. Hardware (GPU names), languages and file formats are not entities.
- `concept`: an abstract idea or interface the publication discusses (`decision model`, `safety classifier`, `System One API`).
- Every occurrence of a surface form is annotated. Nested spans are not annotated (the longest wins).
- A relation is annotated only when both endpoints appear as mentions in the same document and the sentence states the relationship (`made_by`, `built_on`, `measured_by`, `replaces`, `successor_of`, `licensed_under`). Relations whose subject is a pronoun ("It is built on...") are not annotated.

## Annotation format

```
## 0h                      document id
maker: AccuKnox Inc.       kind: surface forms separated by " ; "; "surface=key" maps a variant to a canonical key
model: Guard 1.1 ; Qwen3.5-4B
rel: Guard 1.1 | built_on | Qwen3.5-4B
```

Rebuild the generated files from a DynamoDB scan with
`python scripts/typed_extraction_evaluation/build_dataset.py --scan-json SCAN.json --annotations datasets/typed_extraction_lab/annotations.txt`.

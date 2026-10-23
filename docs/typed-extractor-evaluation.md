# Typed extractor evaluation

This page records the exploration behind the typed-entity extractor (Kanbus story blbs-e14d5c, consumed by blbs-81ec10 and by the Papyrus public knowledge base). The question: can fast extractors built on small decision or span models replace the spaCy pipeline for typed entities (maker, model, task, licence and so on) and typed relations (made_by, built_on, licensed_under and so on), without a language model in production?

The short answer: yes for entities with a known registry, and usably for relations, with a desk review step. **Recommended backend: a registry alias matcher first, then GLiNER2 base (`fastino/gliner2-base-v1`, Apache-2.0, about 205M parameters) at a 0.7 threshold for everything the registry does not cover and for relations.** It scores entity F1 65.3 and relation F1 56.2 against 18.8 and 0 for the current spaCy pipeline, runs on a CPU in a fraction of a second per document with no per-call cost, and sits within two points of the language-model baseline on entities while being roughly 19 times faster in median wall time. It is not good enough to publish without review, which matches the `proposed` state in the extractor contract.

## The evaluation set

- 71 published items from the Shipped publication (public text from https://shipped.anth.us, exported read-only from the `PublishedItem` table).
- 142 documents: each item contributes its headline plus deck and its first body paragraph.
- 756 gold entity mentions across nine kinds and 246 gold relations across six types, in `datasets/typed_extraction_lab/` (documents, closed vocabulary file, annotations, generated gold labels). `datasets/typed_extraction_lab/README.md` states the annotation rules.
- **The gold set was annotated by an AI agent (Claude Sonnet 5.5) acting as a human proxy**, seeded from the editor-entered front-matter entities and extended by reading every document. It was spot-checked on 12 random documents and a surface-form consistency pass, but no human editor has reviewed it. Treat small differences between candidates as noise, and treat the fuzzy kinds (`task`, `technique`, `concept`, `model_family`) with caution: many "false positives" there are plausible entities the annotator did not label.
- Relation support is thin for some types: `measured_by` 7, `replaces` 4, `successor_of` 4 gold relations. Their scores are indicative only.

## Protocol (the same for every candidate)

1. Input: the document text and the closed vocabulary (`vocabulary.yml`). Zero-shot models receive the same short label per kind and per relation type and nothing else: no descriptions, no examples, no per-kind tuning.
2. One document at a time on CPU (Apple M1 Max, 10 cores, torch 2.14.1 default threads), after three untimed warm-up documents. Timed runs use the median of three repetitions per document for the span models. Model load time is reported separately.
3. Threshold: 0.5 for every zero-shot model, fixed before scoring. The sweep at 0.3 and 0.7 and the `hybrid@0.7` row were run afterwards and use the gold labels, so they are optimistic.
4. Registry and resolution: items alternate between two folds. The registry of known entities for a document is built from the gold labels of the other fold, so no candidate sees the gold labels of the document it extracts. After extraction every candidate goes through the same exact normalised-alias resolution step against that registry: a match gives state `resolved` with the entity key, anything else gives `proposed`.
5. Entity match: same kind and span intersection over union of at least 0.5 (lenient, the headline number), or identical span after trimming punctuation (strict). Precision, recall and F1 are micro-averaged per kind and overall; macro F1 averages the kinds. "Untyped F1" ignores the kind and measures span detection only.
6. Relation match: the canonical triple (subject, type, object) must equal a gold triple, where endpoints are canonicalised through the document's gold mention keys.
7. spaCy has a fixed label map (ORG and PERSON to maker, PRODUCT and WORK_OF_ART to model, LAW to licence); labels outside the map are dropped. spaCy emits no typed relations, so its relation score is zero by construction.
8. The `gazetteer` candidate only finds entities that are already in the registry; it has no recall on anything new. `hybrid` is the gazetteer first, then GLiNER2 for spans that do not overlap a registry match.
9. The optional language-model baseline is GPT-6 Luna only, with a hard spend cap of 2 US dollars. It received the same labels as the span models plus a request for JSON output. The run used 33,287 input and 78,624 output tokens (output is large because the model reasons before answering). At the list price from secondary pricing aggregators (0.10 input and 0.50 output USD per million tokens; not confirmed on the OpenAI pricing page) that is about 0.04 USD, or 0.30 USD per 1,000 documents. The run was capped with conservative 5 and 20 USD rates, under which it totalled 1.74 USD, so the cap held under either price.

## Results

All numbers are percentages. Latency was measured while other jobs were running on the same Mac (load average roughly 40 to 60 on 10 cores), so wall-clock figures are pessimistic and noisy (note the median CPU milliseconds column, which is less sensitive to contention but counts every thread). Cost per 1,000 documents for local candidates is zero in API fees; the CPU time is the median CPU milliseconds column multiplied by 1,000.

### Summary

| Candidate | Entity P | Entity R | Entity F1 | Macro F1 | Strict F1 | Untyped F1 | Relation P / R / F1 | Median ms | p95 ms | Median CPU ms | API USD per 1,000 docs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gazetteer | 84.8 | 48.1 | 61.4 | 62.1 | 59.1 | 62.8 | - | 0.2 | 0.4 | 0.2 | 0.00 |
| gliner-medium@0.5 | 55.7 | 45.5 | 50.1 | 40.4 | 45.6 | 65.2 | - | 157.7 | 241.2 | 226.6 | 0.00 |
| gliner-multi@0.5 | 52.7 | 36.1 | 42.9 | 31.4 | 39.9 | 58.6 | - | 349.8 | 691.9 | 275.2 | 0.00 |
| gliner2@0.5 | 41.7 | 65.6 | 51.0 | 43.9 | 48.7 | 60.4 | 41.1 / 64.2 / 50.2 | 352.4 | 457.8 | 507.4 | 0.00 |
| glirel@0.5 | 55.7 | 45.5 | 50.1 | 40.4 | 45.6 | 65.2 | 19.8 / 8.9 / 12.3 | 510.1 | 833.5 | 773.5 | 0.00 |
| hybrid@0.5 | 48.2 | 80.8 | 60.4 | 56.6 | 58.1 | 64.3 | 41.1 / 64.2 / 50.2 | 403.3 | 605.4 | 533.4 | 0.00 |
| hybrid@0.7 | 56.0 | 78.2 | 65.3 | 60.3 | 62.9 | 68.7 | 52.5 / 60.6 / 56.2 | 315.9 | 414.6 | 485.6 | 0.00 |
| llm | 57.5 | 81.1 | 67.3 | 59.0 | 64.8 | 74.3 | 72.8 / 90.2 / 80.6 | 5986.8 | 13368.8 | n/a | 0.30 |
| nuner-zero@0.5 | 31.4 | 47.9 | 37.9 | 29.0 | 18.1 | 44.2 | - | 470.6 | 1030.4 | 639.9 | 0.00 |
| relex@0.5 | 49.6 | 63.4 | 55.6 | 41.0 | 52.8 | 66.2 | 37.4 / 72.8 / 49.4 | 416.3 | 550.7 | 671.7 | 0.00 |
| spacy | 25.9 | 14.8 | 18.8 | 5.6 | 16.7 | 50.5 | - | 9.5 | 17.2 | 9.3 | 0.00 |

### Entity precision / recall / F1 per kind (lenient match)

| Candidate | maker | model | model_family | task | technique | licence | dataset | platform | concept |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gazetteer | 85.9 / 38.6 / 53.3 | 60.9 / 11.8 / 19.7 | 0.0 / 0.0 / 0.0 | 77.1 / 82.8 / 79.8 | 100.0 / 84.4 / 91.6 | 100.0 / 81.0 / 89.5 | 100.0 / 30.0 / 46.2 | 100.0 / 75.0 / 85.7 | 96.7 / 90.6 / 93.5 |
| gliner-medium@0.5 | 94.9 / 59.5 / 73.2 | 63.8 / 52.5 / 57.6 | 45.8 / 57.9 / 51.2 | 33.3 / 7.4 / 12.1 | 17.0 / 17.8 / 17.4 | 82.7 / 79.8 / 81.2 | 30.8 / 40.0 / 34.8 | 27.4 / 54.2 / 36.4 | 0.0 / 0.0 / 0.0 |
| gliner-multi@0.5 | 90.6 / 72.8 / 80.7 | 68.8 / 37.0 / 48.1 | 27.3 / 47.4 / 34.6 | 37.5 / 4.9 / 8.7 | 46.7 / 15.6 / 23.3 | 64.9 / 28.6 / 39.7 | 50.0 / 10.0 / 16.7 | 22.3 / 47.9 / 30.5 | 0.0 / 0.0 / 0.0 |
| gliner2@0.5 | 90.8 / 87.3 / 89.0 | 74.7 / 71.8 / 73.2 | 8.1 / 57.9 / 14.2 | 27.0 / 45.1 / 33.7 | 23.3 / 15.6 / 18.7 | 76.4 / 81.0 / 78.6 | 28.0 / 70.0 / 40.0 | 31.5 / 72.9 / 44.0 | 1.9 / 12.5 / 3.3 |
| glirel@0.5 | 94.9 / 59.5 / 73.2 | 63.8 / 52.5 / 57.6 | 45.8 / 57.9 / 51.2 | 33.3 / 7.4 / 12.1 | 17.0 / 17.8 / 17.4 | 82.7 / 79.8 / 81.2 | 30.8 / 40.0 / 34.8 | 27.4 / 54.2 / 36.4 | 0.0 / 0.0 / 0.0 |
| hybrid@0.5 | 92.1 / 88.0 / 90.0 | 70.2 / 67.2 / 68.7 | 9.0 / 47.4 / 15.1 | 39.8 / 91.0 / 55.4 | 68.4 / 86.7 / 76.5 | 84.1 / 88.1 / 86.0 | 28.6 / 60.0 / 38.7 | 41.9 / 91.7 / 57.5 | 12.2 / 90.6 / 21.5 |
| hybrid@0.7 | 91.5 / 81.6 / 86.3 | 73.4 / 63.9 / 68.3 | 10.7 / 47.4 / 17.5 | 47.4 / 91.0 / 62.4 | 81.2 / 86.7 / 83.9 | 85.9 / 86.9 / 86.4 | 35.7 / 50.0 / 41.7 | 50.0 / 91.7 / 64.7 | 18.8 / 90.6 / 31.2 |
| llm | 86.6 / 94.3 / 90.3 | 78.5 / 87.4 / 82.7 | 20.0 / 73.7 / 31.5 | 42.5 / 74.6 / 54.2 | 40.0 / 40.0 / 40.0 | 96.4 / 96.4 / 96.4 | 47.1 / 80.0 / 59.3 | 63.5 / 83.3 / 72.1 | 2.9 / 12.5 / 4.8 |
| nuner-zero@0.5 | 61.5 / 81.0 / 69.9 | 26.8 / 47.5 / 34.3 | 17.4 / 42.1 / 24.6 | 23.4 / 9.0 / 13.0 | 33.3 / 13.3 / 19.0 | 22.9 / 67.9 / 34.2 | 14.3 / 40.0 / 21.1 | 28.6 / 70.8 / 40.7 | 5.6 / 3.1 / 4.0 |
| relex@0.5 | 92.9 / 90.5 / 91.7 | 64.9 / 76.9 / 70.4 | 10.1 / 42.1 / 16.3 | 34.0 / 29.5 / 31.6 | 21.7 / 22.2 / 22.0 | 64.0 / 67.9 / 65.9 | 10.5 / 80.0 / 18.6 | 41.5 / 70.8 / 52.3 | 0.0 / 0.0 / 0.0 |
| spacy | 26.1 / 58.9 / 36.1 | 26.9 / 7.6 / 11.8 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 11.1 / 1.2 / 2.2 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| gold support | 158 | 238 | 19 | 122 | 45 | 84 | 10 | 48 | 32 |

### Relation precision / recall / F1 per type

| Candidate | made_by | built_on | measured_by | replaces | successor_of | licensed_under |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gazetteer | - | - | - | - | - | - |
| gliner-medium@0.5 | - | - | - | - | - | - |
| gliner-multi@0.5 | - | - | - | - | - | - |
| gliner2@0.5 | 81.1 / 79.2 / 80.2 | 27.1 / 45.7 / 34.0 | 0.0 / 0.0 / 0.0 | 8.0 / 50.0 / 13.8 | 12.0 / 75.0 / 20.7 | 42.0 / 51.5 / 46.3 |
| glirel@0.5 | 44.2 / 14.6 / 22.0 | 0.0 / 0.0 / 0.0 | - | 4.9 / 50.0 / 8.9 | - | 6.7 / 1.5 / 2.5 |
| hybrid@0.5 | 81.1 / 79.2 / 80.2 | 27.1 / 45.7 / 34.0 | 0.0 / 0.0 / 0.0 | 8.0 / 50.0 / 13.8 | 12.0 / 75.0 / 20.7 | 42.0 / 51.5 / 46.3 |
| hybrid@0.7 | 86.6 / 74.6 / 80.2 | 46.9 / 42.9 / 44.8 | 0.0 / 0.0 / 0.0 | 10.5 / 50.0 / 17.4 | 17.6 / 75.0 / 28.6 | 50.8 / 48.5 / 49.6 |
| llm | 84.1 / 93.8 / 88.7 | 55.2 / 91.4 / 68.8 | 25.0 / 71.4 / 37.0 | 100.0 / 75.0 / 85.7 | 60.0 / 75.0 / 66.7 | 77.0 / 86.4 / 81.4 |
| nuner-zero@0.5 | - | - | - | - | - | - |
| relex@0.5 | 74.6 / 72.3 / 73.4 | 17.3 / 65.7 / 27.4 | 7.7 / 57.1 / 13.6 | 12.1 / 100.0 / 21.6 | 10.0 / 75.0 / 17.6 | 49.0 / 77.3 / 60.0 |
| spacy | - | - | - | - | - | - |
| gold support | 130 | 35 | 7 | 4 | 4 | 66 |

### Entity resolution against the registry (lenient-matched mentions only)

| Candidate | Known entities | Resolved correctly | Unresolved alias | Resolved to wrong entity | New entities | New merged into a known one |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gazetteer | 352 | 352 | 0 | 0 | 12 | 12 |
| gliner-medium@0.5 | 126 | 118 | 8 | 0 | 218 | 0 |
| gliner-multi@0.5 | 86 | 78 | 8 | 0 | 187 | 1 |
| gliner2@0.5 | 213 | 201 | 12 | 0 | 283 | 0 |
| glirel@0.5 | 126 | 118 | 8 | 0 | 218 | 0 |
| hybrid@0.5 | 353 | 352 | 1 | 0 | 258 | 12 |
| hybrid@0.7 | 353 | 352 | 1 | 0 | 238 | 12 |
| llm | 270 | 259 | 11 | 0 | 343 | 1 |
| nuner-zero@0.5 | 163 | 65 | 90 | 8 | 199 | 0 |
| relex@0.5 | 178 | 167 | 11 | 0 | 301 | 0 |
| spacy | 43 | 37 | 6 | 0 | 69 | 0 |

### Failure modes

| Candidate | Predicted mentions | No gold overlap | Overlap, wrong kind | Text not in source | Relations predicted | Relation endpoints not in source | Most frequent no-overlap predictions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gazetteer | 429 | 10 | 55 | 0 | 0 | 0 | streaming (task) x6; Laya (model_family) x1; classify (task) x1; V1.1 (model) x1 |
| gliner-medium@0.5 | 618 | 137 | 137 | 0 | 0 | 0 | E2B (model) x3; Base model (model) x3; 31B (model) x2; category (concept) x2 |
| gliner-multi@0.5 | 518 | 113 | 132 | 0 | 0 | 0 | E2B (model) x4; E4B (model) x4; Context (concept) x3; Think (model) x2 |
| gliner2@0.5 | 1190 | 531 | 163 | 0 | 384 | 0 | reasoning (task) x11; 27B (model_family) x9; card (platform) x8; 4B (model_family) x8 |
| glirel@0.5 | 618 | 137 | 137 | 0 | 128 | 0 | E2B (model) x3; Base model (model) x3; 31B (model) x2; category (concept) x2 |
| hybrid@0.5 | 1267 | 536 | 120 | 0 | 384 | 0 | reasoning (task) x11; 27B (model_family) x9; card (platform) x8; 4B (model_family) x8 |
| hybrid@0.7 | 1055 | 365 | 99 | 0 | 284 | 0 | 27B (model_family) x9; probability (concept) x7; streaming (task) x7; 2B (model_family) x7 |
| llm | 1068 | 311 | 142 | 2 | 305 | 0 | reasoning (task) x15; fine-tuned (technique) x7; 31B (model) x4; E2B (model) x4 |
| nuner-zero@0.5 | 1154 | 307 | 485 | 0 | 0 | 0 | . (licence) x53; . (model) x49; model (model) x11; . (platform) x10 |
| relex@0.5 | 966 | 342 | 145 | 0 | 501 | 1 | reasoning (task) x5; probability (concept) x4; weights (concept) x4; 4B (model) x3 |
| spacy | 433 | 100 | 221 | 0 | 0 | 0 | 4B (maker) x10; API (maker) x8; 2B (maker) x8; 8B (maker) x7 |

### Threshold sensitivity (post-hoc, uses the gold labels, so optimistic)

| Candidate and threshold | Entity P | Entity R | Entity F1 | Relation F1 |
| --- | ---: | ---: | ---: | ---: |
| gliner-medium@0.3 | 44.5 | 50.9 | 47.5 | 0.0 |
| gliner-medium@0.5 | 55.7 | 45.5 | 50.1 | 0.0 |
| gliner-medium@0.7 | 66.1 | 38.1 | 48.3 | 0.0 |
| gliner-multi@0.5 | 52.7 | 36.1 | 42.9 | 0.0 |
| gliner2@0.3 | 33.8 | 69.8 | 45.6 | 43.3 |
| gliner2@0.5 | 41.7 | 65.6 | 51.0 | 50.2 |
| gliner2@0.7 | 49.1 | 59.9 | 54.0 | 56.2 |
| glirel@0.5 | 55.7 | 45.5 | 50.1 | 12.3 |
| hybrid@0.5 | 48.2 | 80.8 | 60.4 | 50.2 |
| hybrid@0.7 | 56.0 | 78.2 | 65.3 | 56.2 |
| nuner-zero@0.5 | 31.4 | 47.9 | 37.9 | 0.0 |
| relex@0.5 | 49.6 | 63.4 | 55.6 | 49.4 |

### Versions and configurations

| Candidate | Version and configuration | Load seconds | Peak RSS MB | Load average at end |
| --- | ---: | ---: | ---: | ---: |
| gazetteer | biblicus-evaluation alias matcher (normalised token longest match) | 0.0 | 23 | 18 |
| gliner-medium@0.5 | gliner 0.2.29, torch 2.14.1, urchade/gliner_medium-v2.1, threshold 0.5 | 36.5 | 1698 | 41 |
| gliner-multi@0.5 | gliner 0.2.29, torch 2.14.1, urchade/gliner_multi-v2.1, threshold 0.5 | 28.2 | 2566 | 126 |
| gliner2@0.5 | gliner2 2.1.0, torch 2.14.1, fastino/gliner2-base-v1, threshold 0.5 | 20.5 | 2191 | 46 |
| glirel@0.5 | gliner 0.2.29, torch 2.14.1, urchade/gliner_medium-v2.1, threshold 0.5; glirel 1.2.1, jackboyla/glirel-large-v0, threshold 0.5 | 43.5 | 3074 | 54 |
| hybrid@0.5 | alias matcher + gliner2 2.1.0, torch 2.14.1, fastino/gliner2-base-v1, threshold 0.5 | 22.6 | 2005 | 40 |
| hybrid@0.7 | alias matcher + gliner2 2.1.0, torch 2.14.1, fastino/gliner2-base-v1, threshold 0.7 | 19.2 | 2273 | 48 |
| llm | openai 3.36.1, gpt-6-luna | 1.6 | 86 | 0 |
| nuner-zero@0.5 | gliner 0.2.29, torch 2.14.1, numind/NuNER_Zero, threshold 0.5 | 30.1 | 4095 | 42 |
| relex@0.5 | gliner 0.2.29, torch 2.14.1, knowledgator/gliner-relex-large-v1.0, threshold 0.5 | 43.2 | 3397 | 49 |
| spacy | spacy 3.8.16, en_core_web_sm 3.7.1 | 7.2 | 353 | 18 |

## Findings

**spaCy is not a candidate for typed entities.** Entity F1 18.8 (macro 5.6). It recovers some organisations (maker F1 36) but labels size tokens such as `4B` and `API` as organisations, and it has no notion of licence, task, technique, dataset or platform. It also emits no typed relations. Span detection alone (untyped F1 50.5) is not the problem; the label set is.

**Zero-shot span models split into usable and not.** GLiNER2 base and GLiNER-relex large are the strongest local models on entities (F1 51.0 and 55.6 at the fixed 0.5 threshold) and the only local models that also extract relations. GLiNER medium and multilingual v2.1 are precise on makers and licences but weak on everything else; NuNER Zero was poor under this label set (it emitted many bare punctuation spans, 485 wrong-kind overlaps). GLiREL needs entity spans from a separate model, was far weaker than GLiNER2's built-in relation head (relation F1 12.3), and its weights are CC BY-NC-SA 4.0, which rules it out for production.

**A registry beats a model on repeated entities.** The alias matcher alone reaches entity F1 61.4 with 84.8 precision because makers, licences, platforms, techniques and concepts repeat across items, and it takes under a millisecond. Its recall is only 48.1, since models are mostly new. Combining it with GLiNER2 gives the highest recall of any non-LLM candidate (78.2 at threshold 0.7) and the best kind-level scores for technique (84), licence (86) and platform (65). The result depends on registry growth: with an empty registry the system falls back to GLiNER2 alone (F1 54.0).

**The language model is better on relations, and about equal on entities.** GPT-6 Luna has entity F1 67.3 and relation F1 80.6, against 65.3 and 56.2 for the recommended hybrid. It takes about 6 seconds per document (p95 13 seconds) and costs money per call. The production decision (no language model for extraction) holds for entities, which are within two points. The relation gap of 24 points is real: it is largest on `built_on` (45 against 69) and `licensed_under` (50 against 81), the two common types after `made_by` (80 against 89). Relations from the recommended backend should therefore always be `proposed` and shown to the desk, and the cheapest next improvement is to fine-tune GLiNER2 on desk-confirmed relations or add a rule for `licensed_under` (a licence mention in the same headline or sentence as the model), both follow-up work.

**Failure modes seen**

- *Spurious spans.* Span models propose plausible but unlabelled spans: size tokens as `model_family` (`27B`, `4B`), the word `reasoning` as a task, `card` and `probability` as platform or concept. These land in the `proposed` state and are cheap to reject, but they dominate the false positives of GLiNER2 (531 spans with no gold overlap at 0.5).
- *Wrong kind.* 55 to 485 mentions overlap a gold span with a different kind, mostly `model` against `model_family`, `task` against `concept` and `platform` against `licence`.
- *Hallucinated entities.* Extractive models cannot invent text: every span GLiNER2 and the registry return exists in the source. The language model produced 2 entity strings that are not in the source, and no relation endpoint was missing from the source for GLiNER2 or the language model.
- *Unresolved aliases.* Known entities left unresolved because the span boundary differs from the registered alias: 12 of 213 for GLiNER2, 1 of 353 for the hybrid. No span model resolved a mention to the wrong entity.
- *Prefix merging in the alias matcher.* 12 mentions of entities new to the registry were merged into a shorter known alias by longest-token matching, for example `Gemma-3-4B-it` resolved to `Gemma 3`, `Qwen3-TTS` to `Qwen3`. The extractor must resolve a mention only when its whole normalised text equals an alias, and must never merge fuzzily, which is already the rule in blbs-81ec10.
- *Kinds that need data, not prompting.* `model_family` (F1 17 for the hybrid) and `concept` (31) are unreliable zero-shot because the vocabulary labels are abstract. The remedy is to fine-tune GLiNER2 on desk-confirmed entities later, not to add prompting.

## Recommendation

Implement blbs-81ec10 with a backend interface and ship **GLiNER2 base with the registry alias matcher in front** as the default:

| Item | Value |
| --- | --- |
| Entity spans and relations | `fastino/gliner2-base-v1`, revision `f9634218e53580c56edf0de97ca1a7d3f1c2354e`, Apache-2.0, 834 MB of weights, about 2 GB resident |
| Library | `gliner2` 2.1.0 (Apache-2.0), `torch` 2.14.1, `transformers` 5.16.1 |
| Resolution | normalised exact alias match against the accepted-entity registry (no model) |
| Threshold | 0.7 (entities and relations); the 0.5 default and 0.3 sweep are in the table above |
| Runtime | CPU is sufficient; about 0.3 to 0.4 seconds per short document on a contended 10-core Mac, no GPU, no network, no per-call cost |
| Install | `pip install gliner2` (pulls torch and transformers), model downloaded from Hugging Face on first use; run as a job, not in a Lambda bundle |

Second choices: `knowledgator/gliner-relex-large-v1.0` (Apache-2.0, 1.9 GB) is the best local candidate on relation recall (72.8) and entity F1 at 0.5 (55.6), but is slower and bigger; evaluate it again once there is desk-confirmed training data. Do not use GLiREL (non-commercial licence) or NuNER Zero under this vocabulary. The existing spaCy pipeline stays only for the untyped graph extractors it already serves. A language model is not needed in production; if a future evaluation wants one as a repair tier, the GPT-6 Luna numbers above are the baseline to beat per request.

## Proposed interface for blbs-81ec10

The extractor follows the typed application programming interface conventions (a Pydantic request model, a Pydantic response model, a plain function, a thin command).

Command:

```
biblicus extract typed-entities
  --corpus CORPUS
  --vocabulary vocabulary.yml
  [--registry registry.json]
  [--backend gliner2]
  [--threshold 0.7]
  [--item-id ID ...]
  [--out DIR]
```

Inputs:

- `vocabulary`: the closed vocabulary file (`entity_kinds` and `relation_types`, each with a key and a short label), as in `datasets/typed_extraction_lab/vocabulary.yml`.
- `registry`: optional JSON list of accepted entities, `[{"key", "kind", "aliases": []}]`; absent means every mention is proposed.
- `backend`, `threshold`: backend id and score threshold; both are written into the output and into the cache identity together with the vocabulary hash and the text hash, so the same input is served from cache with identical output.
- Items come from the corpus; each item's text is processed in paragraph-sized windows and offsets are reported against the item text.

Output (stdout and `--out`), one JSON document:

```json
{
  "schema_version": 1,
  "vocabulary": {"publication": "shipped", "version": 1, "hash": "..."},
  "backend": {"id": "gliner2", "model": "fastino/gliner2-base-v1", "revision": "f9634218e5...", "threshold": 0.7},
  "items": [
    {
      "item_id": "published-item-decisions-accuknox-guard-1-1",
      "entities": [
        {"id": "e1", "kind": "maker", "text": "AccuKnox Inc.", "state": "resolved",
         "entity_key": "accuknox inc", "span": {"start": 0, "end": 13}, "score": 0.99},
        {"id": "e2", "kind": "model", "text": "Guard 1.1", "state": "proposed",
         "entity_key": null, "span": {"start": 23, "end": 32}, "score": 0.98}
      ],
      "relations": [
        {"id": "r1", "type": "made_by", "subject": "e2", "object": "e1", "state": "proposed",
         "span": {"start": 0, "end": 32}, "score": 0.97}
      ]
    }
  ],
  "summary": {"items": 1, "entities": 2, "resolved": 1, "proposed": 1, "relations": 1}
}
```

Rules: `kind` and relation `type` come only from the vocabulary; `state` is `resolved` when the mention matches a registry alias exactly after normalisation (case, spacing and punctuation), otherwise `proposed`; a relation is `resolved` only when both endpoints are resolved; entity spans are character offsets into the item text and a relation span covers both endpoints; fuzzy merging of distinct entities never happens. Failures use the shared command failure envelope. Papyrus maps the output onto the existing graph export shape (generated nodes, Papyrus owns acceptance).

## Reproduce

```
aws dynamodb scan --profile papyrus-production --region us-east-1 \
  --table-name PublishedItem-6sw6454pozbgvdgm233gqkxsxu-NONE > scan.json
python scripts/typed_extraction_evaluation/build_dataset.py --scan-json scan.json \
  --annotations datasets/typed_extraction_lab/annotations.txt
python scripts/typed_extraction_evaluation/run_candidates.py --candidate gliner2 --threshold 0.7 --repeats 3 --out results
python scripts/typed_extraction_evaluation/score.py --results results --out scores.json
python scripts/typed_extraction_evaluation/report.py --scores scores.json --out report.md
```

Candidate names for `--candidate`: `spacy`, `gazetteer`, `gliner-medium`, `gliner-multi`, `nuner-zero`, `gliner2`, `relex`, `glirel`, `hybrid`, `llm` (needs `OPENAI_API_KEY`, and `--price-in`, `--price-out` and `--budget-usd` for the spend cap). The environment used: Python 3.12, `gliner` 0.2.29, `gliner2` 2.1.0, `glirel` 1.2.1, `spacy` 3.8.16 with `en_core_web_sm` 3.7.1 from the Hugging Face `spacy/en_core_web_sm` repository, `torch` 2.14.1, `openai` 3.36.1. The scored results of the run described here are in `datasets/typed_extraction_lab/results/scores.json`.

Model revisions: `urchade/gliner_medium-v2.1` 40ec419335d0 (Apache-2.0), `urchade/gliner_multi-v2.1` 443d26d654e0 (Apache-2.0), `numind/NuNER_Zero` c90187673f46 (MIT), `fastino/gliner2-base-v1` f9634218e53 (Apache-2.0), `knowledgator/gliner-relex-large-v1.0` 4aedc9226a5a (Apache-2.0), `jackboyla/glirel-large-v0` 40a523e12a84 (CC BY-NC-SA 4.0 per the model card), `spacy/en_core_web_sm` 8fb6f8155286 (MIT).

## Limits of this evaluation

- One annotator, an AI agent; no inter-annotator agreement was measured.
- 142 short documents from one publication; small relation support for three of the six types.
- The headline threshold was fixed in advance, but the 0.7 recommendation and the hybrid row come from a post-hoc sweep on the same labels.
- The registry is built from gold labels of the other fold, which is the best case for the alias matcher (every registered entity is correctly labelled).
- Latency was measured on a busy machine.

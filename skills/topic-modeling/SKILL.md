---
name: topic-modeling
description: Use when doing topic modeling on a corpus, especially when transcribing call recordings, extracting a key customer intent string from each transcript, handling Not Applicable cases, and running/reviewing BERTopic-style topic models over derived summaries or corpus text.
---

# Topic Modeling

Use this skill when preparing a corpus for topic modeling, especially for audio-call corpora where raw recordings are transcribed and each call needs a derived topic-modeling text.

Summarizing original corpus items to a **key customer intent** is not the only way to topic model a corpus. Topic modeling can run over full transcripts, chunks, document summaries, metadata-enriched text, search snippets, or other representations. Key customer intent extraction is a common task for call corpora because it reduces long noisy transcripts into comparable customer-purpose strings.

## Workflow

1. Create or update the project-management task before corpus work.
2. Initialize the corpus locally and ingest only intended raw items.
3. Build an extraction snapshot for source modality conversion, such as speech-to-text for audio.
4. Validate extracted text manually before summarization or modeling.
5. Run a small pilot first, usually 50 items.
6. Review examples from every important class, especially `Not Applicable`.
7. Refine the extraction prompt until the pilot outputs are useful topic-modeling features.
8. Run the full corpus only after the pilot behavior is acceptable, using parallel LLM extraction for large corpora.
9. Export a review CSV with item identifiers, source paths, derived text, `Not Applicable` flags, topic ids, labels, and topic keywords.

## Audio Folder to Topic Analysis Checklist

When starting with a folder full of recordings:

1. Confirm the source folder and file types before ingest. Ingest only the intended audio files, such as `*.mp3`; leave adjacent JSON, logs, or root metadata files out of the corpus unless they are the subject of analysis.
2. Initialize the local corpus and reindex after ingest so every item has a stable corpus item id, source URI, tags, and media type.
3. Verify secrets before long-running jobs. Store provider keys in the project's ignored local config, not in committed files or command history.
4. Run transcription as a reusable extraction snapshot. Do not retranscribe unless the speech-to-text configuration changes.
5. Inspect the extraction manifest for total, extracted, empty, and errored items. Keep empty and errored recordings traceable, but exclude them from customer-only topic modeling.
6. Run a fixed-size pilot for intent extraction and topic modeling before the full corpus.
7. Iterate the prompt on real examples, especially false `Not Applicable` calls and boilerplate-heavy summaries.
8. Run the full intent extraction with `llm_extraction.max_workers` and a stable cache identity so restarting with higher concurrency does not regenerate existing intent strings.
9. Produce both a canonical JSON output and delivery-oriented CSV/Markdown summaries. If a generated CSV has quote or newline problems, regenerate a clean CSV from canonical JSON/JSONL artifacts instead of treating the CSV as the source of truth.

## Audio Call Transcription

For call recordings, prefer diarized transcription when available.

For Deepgram call transcription, a practical baseline is:

- `stt-deepgram` with `model: nova-3`, `language: en`, `punctuate: true`, `smart_format: true`, `diarize: true`, and `filler_words: false`.
- A transform stage that emits speaker-labeled lines joined with newlines.

Use speaker-labeled utterances for the downstream intent extractor. If a provider returns only word-level speaker labels, transform word-level speaker changes into speaker-labeled text before LLM extraction.

Validate several transcripts before modeling:

- Speaker labels are present.
- The transcript is non-empty.
- Short failed calls remain short instead of hallucinated.
- The transcript path can be traced back to the corpus item id and source recording.

## Key Customer Intent Extraction

The key customer intent should be one single-line string optimized for topic modeling. It should start with distinctive topic words, not boilerplate.

Good:

```text
Shipping status inquiry for a delayed order with a request to confirm the expected delivery date; "I expected it this week."
```

Bad:

```text
Customer called to check on an order. Quote: "I expected it this week."
```

Avoid repeated labels and framing phrases because they become dominant topic-modeling features:

- Do not start with `Customer called to`, `Customer is calling to`, `Caller wants`, `The customer needs`, or `Request to`.
- Do not include labels such as `Quote`, `Evidence`, or `Customer said`.
- Do not include generic call-center words unless essential to the intent.
- Do not include transcript metadata, timestamps, speaker labels, time offsets, or unclear numeric fragments.

Include short quoted customer evidence when useful, but make it bare quoted text after the intent:

```text
Order change request from bulk shipment to palletized shipment; "Please switch that from bulk to pallets."
```

Use only words actually spoken by the customer inside quoted text. If no reliable customer quote is available, omit the quote and still return a detailed intent string.

## Not Applicable Rules

Use `Not Applicable` sparingly. A call is not `Not Applicable` just because it is short or only contains a transfer request.

Valid customer intents include:

- Department routing, person routing, callback, transfer, or voicemail requests.
- Sales follow-up, quote discussion, purchase approval, order commitment, or deal-closing language.
- Noisy transcripts that still contain a plausible customer request or purchase signal.

Examples that should be applicable:

```text
Accounts department transfer request; "Could I be connected to accounts?"
```

```text
Purchase commitment for a product; "Let's buy one."
```

Return exactly `Not Applicable` only when the transcript is:

- Not customer-facing.
- Agent-to-agent or internal with no customer request.
- Silent or empty.
- An automated carrier message or voicemail greeting with no customer message.
- Too incoherent to identify any observable customer request or purchase signal.

Examples that can remain `Not Applicable`:

```text
Speaker 0: Hello? Hello? Hello? Hello?
```

```text
Speaker 0: We're sorry. Your call cannot be completed at this time. Please hang up and try your call again later. Thank you.
```

## Prompt Template Pattern

Use a prompt with these constraints:

```text
Read the speaker-labeled call transcript below.

Produce the key customer intent as one detailed string that captures the observable customer request, the specific object involved, and the outcome or requested next step when clear.
Infer the customer from the conversation, but do not assume a fixed speaker number.

Treat department routing, person routing, callback, transfer, or voicemail requests as valid customer intents when that is the observable purpose of the call.
If the customer only asks to reach a department or person, summarize that as a routing intent such as "Billing department transfer request" or "Sales representative callback request".
Treat sales follow-up, quote discussion, purchase approval, order commitment, deal-closing language, or phrases such as "let's buy one" as valid customer intents even when the transcript is short or noisy.
When a transcript is noisy but contains any plausible customer request or purchase signal, return the best observable intent instead of "Not Applicable".

Return exactly "Not Applicable" only when the transcript is not a customer-facing call, is an agent-to-agent or internal call with no customer request, is silent or empty, is an automated carrier or voicemail greeting with no customer message, or contains no observable customer request or purchase signal.

Start with distinctive topic words such as "Shipping status", "Order change", "Delivery instructions", "Invoice dispute", or "Product availability".
Do not start with generic phrases such as "Customer called to", "Customer is calling to", "Caller wants", "The customer needs", or "Request to".
Do not include generic call-center words unless they are essential to the intent.
Do not include transcript metadata, timestamps, speaker labels, time offsets, or unclear numeric fragments.
Include dates, order numbers, purchase order numbers, product dimensions, and quantities only when they are clearly part of the customer's issue.
When a relevant customer quote is available, include one short quote from the customer after the intent using this form: <specific intent>; "<customer words>"
Use only words actually spoken by the customer inside the quote.
If no reliable customer quote is available, omit the quoted evidence and still return a detailed intent string.
Do not use labels such as "Quote", "Evidence", or "Customer said".

Transcript:
{text}
```

For large corpora, set `llm_extraction.max_workers` to run the intent extraction concurrently. Reusing the same prompt and model lets the LLM extraction cache preserve already-generated intent strings when changing only the worker count.

When restarting after a slow sequential run, seed or reuse the existing LLM extraction cache before launching the parallel run. The cache identity should include the prompt, method, and model, but should not include `max_workers` or secret API keys.

## Pilot Review

For every prompt revision, rerun the same pilot sample and compare:

- `Not Applicable` count and examples.
- Presence of generic boilerplate prefixes.
- Presence of repeated quote/evidence labels.
- Whether routing-only calls are treated as valid intents.
- Whether short purchase or sales follow-up calls are treated as valid intents.
- Whether automated greetings, failed calls, and dead-air calls remain `Not Applicable`.

Use simple string checks in addition to human review:

```text
quote_label_count == 0
boilerplate_prefix_count == 0
```

Inspect at least three positive intents and three remaining `Not Applicable` transcripts before moving from pilot to full run.

## Provider-Generated Summaries

Provider summary fields are a valid alternate representation for topic modeling, but treat them as a separate analysis surface from custom key-intent summaries.

Before modeling provider summaries:

1. Verify the provider summary fields are actually populated. Some provider responses include summary-related keys that are empty because summarization was not enabled.
2. If summaries must be generated after transcription, keep them as a separate cached artifact keyed by corpus item id, then merge them back into provider JSON only for delivery/export.
3. Preserve the original provider JSON and produce an updated provider JSON export separately. Do not overwrite raw provider responses unless the workflow explicitly calls for a derived artifact.
4. Run topic modeling over the summary text only, not over full provider JSON or transcript text.
5. Apply the same document eligibility set used by the primary analysis. If the primary customer-intent model excludes `Not Applicable`, internal, empty, or errored calls, exclude the same item ids from provider-summary topic modeling. Otherwise the provider-summary model will include calls that the primary customer-intent analysis intentionally removed.
6. Keep a summary-only JSONL or CSV with `document_id`, `source_item_id`, summary text, topic id, topic label, and topic keywords.

Provider summaries often include boilerplate such as `customer`, `agent`, `speaker`, `representative`, `call`, `asks`, and `says`. If these dominate topic keywords, rerun with a content-focused stop-word list before interpreting the categories. Keep both outputs if useful:

- **Raw provider-summary topics** show how the provider summaries cluster with minimal transformation.
- **Content-focused provider-summary topics** are usually better for business interpretation after removing summary-format boilerplate.

Use provider-summary topic modeling as corroboration unless its summaries were explicitly designed for the target question. For call corpora, custom key customer intent strings are usually more interpretable because they encode the business question directly.

## Comparing Representations

When comparing topic models built from different text representations, make them as apples-to-apples as possible:

- Use the same corpus snapshot.
- Use the same item ids and exclusion policy.
- Use the same BERTopic parameters when possible.
- Report the document count for each model.
- Call out when one representation includes calls excluded from another.
- Compare only stable high-level themes unless both representations have comparable text quality.

If two representations produce the same major themes but one has noisy or artifact-heavy clusters, present the cleaner representation as the primary result and the noisier representation as directional validation.

## Topic Modeling Guidance

Run the topic model over the chosen representation, such as key customer intent strings, not accidentally over full transcripts if the goal is customer-intent clustering.

For customer intent modeling:

- Keep `Not Applicable` rows traceable in the review CSV.
- Consider excluding `Not Applicable` from customer-only topic modeling so it does not form an artificial topic.
- Exclude transcription errors and empty transcripts from customer-only topic modeling, but keep counts for reporting.
- Preserve corpus item ids and source paths through every artifact.
- Save the canonical topic output JSON, LLM extraction JSONL, review CSV, and a concise summary for delivery.
- Treat canonical JSON/JSONL as the source of truth. CSV is a review/export format and may need regeneration if quoted customer evidence contains problematic punctuation or line breaks.

If topics are dominated by repeated prompt artifacts, revise the extracted text format before changing BERTopic parameters.

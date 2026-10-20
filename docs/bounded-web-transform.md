# Bounded web transformation

Run from the Biblicus checkout with Python 3.10–3.13 and the normal core dependencies. No OpenAI SDK or DSPy is used. The offline handoff was tested with Python 3.12, Pydantic 2.13.5 and Behave 1.3.3.

```sh
printf '%s' '{"extracted_text":"Article body.","source_uri":"https://example.org/article","reference_title":"Article","original_title":"","original_subtitle":"","model":"gpt-5.4-mini-2026-03-17"}' | python -m biblicus extract article-text --input-json - --format json
printf '%s' '{"extracted_text":"Article body.","source_uri":"https://example.org/article","reference_title":"Article","original_title":"","original_subtitle":""}' | python -m biblicus summarize map-reduce --task summary --model gpt-5.4-mini-2026-03-17 --input-json - --format json
```

`--input-json -` reads one UTF-8 JSON object from stdin; a path reads one local JSON file. Unknown fields and wrong types fail validation. extracted_text must be nonempty. Context strings default to empty. Article input requires model; metadata model is required on the command line. The only model is gpt-5.4-mini-2026-03-17.

Success exits 0 and writes one JSON object to stdout, with no stderr. Article output has status=ok, text, span_count, prompt_version, model, warnings=[], error=null, retry_trace=[], retry_failure_count=0, retry_rounds_used=0. It selects ordered paragraph IDs, reconstructing exact source passages separated by blank lines; it cannot invent article text. Metadata output has status=ok, task, value, prompt_version, model, map_reduce={map_calls:1,reduce_calls:1,chunk_count:1}, warnings=[], error=null and the same zero retry metadata. It maps the complete admitted source once and reduces those notes for the requested field. Oversized sources are rejected, never clipped or silently chunked.

Failure writes the shared command failure envelope to stdout, `{"status":"failed","error":{"code":...,"message":...,"details":{}}}`, and nothing to stderr; see "Failures" in the typed application programming interface page. It exits 2 for invalid_input, input_too_large and invalid_configuration, which reject the request or its configuration before the call, and 1 for provider_failed and invalid_provider_output, which fail the operation. A failure that happened after the transformation started carries the prompt version, model, task, warnings, map-reduce counts and retry counters in error.details; the article and metadata response fields (text, value) appear only on success. Argument syntax errors use argparse stderr and exit 2. Raw provider bodies, capability values, and source text are never copied into errors.

The worker requires OPENAI_API_KEY and an explicit OPENAI_BASE_URL ending in /provider/v1. If OPENAI_API_BASE is supplied it must match. Only HTTP loopback IPv4/IPv6/localhost endpoints are accepted. OPENAI_MAX_RETRIES, when set, must be 0; the worker always performs zero retries. The worker reads no credential files, .env or user configuration, follows no redirects, uses no environment HTTP proxy and installs nothing. Its sole network destination is POST <OPENAI_BASE_URL>/responses, with Bearer capability. No source or converter destinations are contacted by these commands. Existing URL conversion remains a separate earlier operation.

Requests contain exactly model,input,text,max_output_tokens (2000). Source/context is JSON in a user message; developer instructions treat it as untrusted data. The gateway counts the complete serialized payload plus its 1024-token framing allowance, rejects over 12000 input tokens, pins model and forces storage/tier/reasoning policy. The worker additionally bounds stdin and serialized requests by byte count. There is no alternate destination or automatic retry, including after 409, 429, 502, timeouts or malformed output. Article uses one request, each metadata command two, so a complete job uses at most seven. A denied map prevents reduce. Cancellation/expiry is enforced by the gateway before each dispatch; an already dispatched call may complete, and the integration must discard late results. There is no provider rollback. Each HTTP operation has a 45-second timeout.

Offline verification: PYTHONPATH=src python -m behave --stage bounded features/bounded_web_transform.feature. Tests use disposable loopback servers, fake capabilities and no external provider.

Example article success (identity/retry fields are always present):

```json
{"status":"ok","prompt_version":"bounded-web-v2","model":"gpt-5.4-mini-2026-03-17","task":null,"text":"Article body.","span_count":1,"value":"","map_reduce":{},"warnings":[],"error":null,"retry_trace":[],"retry_failure_count":0,"retry_rounds_used":0}
```

Example metadata success uses task=summary, value="Grounded summary", text="", span_count=0 and map_reduce={"map_calls":1,"reduce_calls":1,"chunk_count":1}. Example denied request prints {"status":"failed","error":{"code":"provider_failed","message":"Gateway request failed; no retry was attempted.","details":{}}} and exits 1. Neither the failure envelope nor stderr includes the provider response body.

The request byte ceiling is 65536; stdin/file JSON ceiling is 262144 UTF-8 bytes; response ceiling is 262144 bytes. Token admission belongs to the trusted gateway, so a byte-admitted request can still fail the gateway token check. No worker tokenizer downloads occur. No new runtime dependency was added.

Verification at implementation handoff: 53 offline BDD scenarios pass with 100% statement and branch coverage for web_transform.py, Ruff passes and Black passes for the new files. Existing URL/GROBID/HTML tests return 19 passing and 7 failing both here and against baseline d3ba6cb sources. The default BDD loader independently fails on the existing missing _extract_latest_failure_error_from_messages import. The bounded stage shares the conventional step file through a symlink, keeping both normal discovery and isolated verification available.

## Quality context (bounded-web-v2)

Both input objects accept source_publication_date (ISO YYYY-MM-DD or null), source_is_archived (boolean or null), and generated_title (string, default empty). Supply the confirmed source date and archive flag, and pass the generated title when generating a subtitle. Unknown values stay null/empty; the worker never substitutes intake time or infers publication dates from the URL. All context reaches both map and reduce. Archived material is described historically; a known publication year must appear in a generated title or the command fails with invalid_provider_output.

A subtitle must add a concrete detail absent from the supplied generated_title. Normalized case-insensitive word-set Jaccard similarity >=0.8 is rejected with invalid_provider_output. This is a transparent lexical guard, not proof of semantic distinctness; no extra model/repair calls occur. With no generated_title the prompt still requests complementary detail, but pairwise validation requires the caller to provide it.

Article selection explicitly excludes legal/privacy notices, general website security banners, feedback requests and footer boilerplate, including security-related wording outside the article. Preserve substantive incident mitigations and historical/archive evidence. Offline regressions verify prompts, context propagation, exact source reconstruction and deterministic output guards; they do not establish improved live-model quality.

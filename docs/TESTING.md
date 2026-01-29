# Testing and coverage

Behavior specifications are written in `features/*.feature` and executed with Behave.

Coverage is measured across the `src/biblicus/` package, excluding vendored third-party libraries, and a Hypertext Markup Language report is written to `reports/htmlcov/index.html`.

## Run tests

Run the test suite without integration downloads:

```
python3 scripts/test.py
```

Run the test suite including integration scenarios that download public test data at runtime:

```
python3 scripts/test.py --integration
```

Run the test suite including optical character recognition integration scenarios:

```
python3 scripts/test.py --integration --ocr
```

Run the test suite including Unstructured integration scenarios:

```
python3 scripts/test.py --integration --unstructured
```

## Integration datasets

Integration scenarios are tagged `@integration`.

The repository does not include downloaded content. Integration scripts download content into a corpus path you choose and then ingest it for a test run.

- Wikipedia summaries: `scripts/download_wikipedia.py`
- Portable Document Format samples: `scripts/download_pdf_samples.py`
- Image samples: `scripts/download_image_samples.py`
- Mixed modality samples: `scripts/download_mixed_samples.py`
- Audio samples: `scripts/download_audio_samples.py`

## Optional integrations in tests

Some integrations require credentials, such as speech to text.

Those are covered by unit-style behavior specifications using fake libraries, not by integration scenarios.

Optical character recognition integration scenarios are tagged `@ocr` and are excluded unless you pass `--ocr`.

Unstructured integration scenarios are tagged `@unstructured` and are excluded unless you pass `--unstructured`.

# Testing and coverage

Behavior specifications are written in `features/*.feature` and executed with Behave.

Coverage is measured across the `src/biblicus/` package and an Hypertext Markup Language report is written to `reports/htmlcov/index.html`.

## Run tests

Run the test suite without integration downloads:

```
python3 scripts/test.py
```

Run the test suite including integration scenarios that download public test data at runtime:

```
python3 scripts/test.py --integration
```

## Integration datasets

Integration scenarios are tagged `@integration`.

The repository does not include downloaded content. Integration scripts download content into a corpus path you choose and then ingest it for a test run.

- Wikipedia summaries: `scripts/download_wikipedia.py`
- Portable Document Format samples: `scripts/download_pdf_samples.py`


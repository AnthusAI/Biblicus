# Demos

This document is a set of runnable examples you can use to see the current system working end to end.
Each section links to a textbook chapter so you can read the concept and then run the code.

For the ordered plan of what to build next, see `docs/roadmap.md`.

## Working examples you can run now

Use the examples in order if you are new to the system. They build from ingestion to extraction, retrieval,
evaluation, and analysis.

### Install for local development

From the repository root:

```
python -m pip install -e ".[dev]"
```

### Create a corpus and ingest a few items

```
rm -rf corpora/demo
python -m biblicus init corpora/demo

python -m biblicus ingest --corpus corpora/demo --note "Hello from a note" --title "First note" --tags "demo,notes"

printf "A tiny text file\n" > /tmp/biblicus-demo.txt
python -m biblicus ingest --corpus corpora/demo /tmp/biblicus-demo.txt

python -m biblicus ingest --corpus corpora/demo https://example.com

python -m biblicus list --corpus corpora/demo
```

### Show an item

Copy an item identifier from the list output, then run:

```
python -m biblicus show --corpus corpora/demo ITEM_ID
```

### Edit raw files and reindex

The catalog is rebuildable. You can edit raw files or sidecar metadata, then refresh the catalog.

```
python -m biblicus reindex --corpus corpora/demo
```

### Crawl a website prefix

To turn a website section into corpus items, crawl a root page and restrict the crawl to an allowed prefix.

In one terminal, create a tiny local website and serve it:

```
rm -rf /tmp/biblicus-site
mkdir -p /tmp/biblicus-site/site/subdir
cat > /tmp/biblicus-site/site/index.html <<'HTML'
<html>
  <body>
    <a href="page.html">Page</a>
    <a href="subdir/">Subdir</a>
  </body>
</html>
HTML
cat > /tmp/biblicus-site/site/page.html <<'HTML'
<html><body>hello</body></html>
HTML
cat > /tmp/biblicus-site/site/subdir/index.html <<'HTML'
<html><body>subdir</body></html>
HTML

python -m http.server 8000 --directory /tmp/biblicus-site
```

In another terminal:

```
rm -rf corpora/crawl-demo
python -m biblicus init corpora/crawl-demo
python -m biblicus crawl --corpus corpora/crawl-demo \
  --root-url http://127.0.0.1:8000/site/index.html \
  --allowed-prefix http://127.0.0.1:8000/site/ \
  --max-items 50 \
  --tag crawled
python -m biblicus list --corpus corpora/crawl-demo
```

### Build an extraction snapshot

Text extraction is a separate pipeline stage from retrieval. An extraction snapshot produces derived text artifacts under the corpus.

This extractor reads text items and skips non-text items.

```
python -m biblicus extract build --corpus corpora/demo --step pass-through-text
```

The output includes a `snapshot_id` you can reuse when building a retrieval backend.

Text extraction details: `docs/extraction.md`

### Graph extraction demo

Graph extraction runs after text extraction and writes to a Neo4j backend. The demo script will reuse the latest extraction
snapshot or build a minimal one if needed.

```
python scripts/graph_extraction_demo.py --corpus corpora/demo --build-extraction --prepare-demo --verify
```

Graph extraction details: `docs/graph-extraction.md`

### Graph extraction integration run

Use the integration script to download a small Wikipedia corpus, run extraction, and build a Neo4j graph snapshot
with the `simple-entities` extractor.

```
python -m pip install neo4j
```

```
python scripts/graph_extraction_integration.py \
  --corpus corpora/wiki_graph_demo \
  --force \
  --verify \
  --report-path reports/graph_extraction_story.md
```

The report written to `reports/graph_extraction_story.md` summarizes the run in a shareable format.

Graph extraction details: `docs/graph-extraction.md`

### Topic modeling integration run

Use the integration script to download AG News, run extraction, and run topic modeling with a single command.
Install optional dependencies first:

```
python -m pip install "biblicus[datasets,topic-modeling]"
```

```
python scripts/topic_modeling_integration.py --corpus corpora/ag_news_demo --force
```

Topic modeling details: `docs/topic-modeling.md`

### Extraction evaluation demo run

Use the extraction evaluation demo to build an extraction snapshot, write a labeled dataset from AG News items, and evaluate
coverage and accuracy.

Install optional dependencies first:

```
python -m pip install "biblicus[datasets]"
```

```
python scripts/extraction_evaluation_demo.py --corpus corpora/ag_news_extraction_eval --force
```

The script prints the dataset path, extraction snapshot reference, and evaluation output path so you can inspect the results.

Extraction evaluation details: `docs/extraction-evaluation.md`

### Extraction evaluation lab run

Use the lab script for a fast, fully local walkthrough with bundled files and labels:

```
python scripts/extraction_evaluation_lab.py --corpus corpora/extraction_eval_lab --force
```

The lab writes a generated dataset file and evaluation output path and prints both in the command output.

Extraction evaluation lab details: `docs/extraction-evaluation.md`

### Retrieval evaluation lab run

Use the retrieval evaluation lab to build a tiny corpus, run extraction, build a retrieval backend, and evaluate it
against bundled labels:

```
python scripts/retrieval_evaluation_lab.py --corpus corpora/retrieval_eval_lab --force
```

The script prints the dataset path, retrieval snapshot identifier, and evaluation output location.

Retrieval evaluation details: `docs/retrieval-evaluation.md`

Run with a larger corpus and a higher topic count:

```
python scripts/topic_modeling_integration.py \
  --corpus corpora/ag_news_demo \
  --force \
  --limit 10000 \
  --vectorizer-ngram-min 1 \
  --vectorizer-ngram-max 2 \
  --bertopic-param nr_topics=8 \
  --bertopic-param min_topic_size=2
```

The command prints the analysis snapshot identifier and the output path. Open the `output.json` file to inspect per-topic labels,
keywords, and document examples.

### Profiling analysis demo

The profiling demo downloads AG News, runs extraction, and produces a profiling report.

```
python scripts/profiling_demo.py --corpus corpora/profiling_demo --force
```

Profiling details: `docs/profiling.md`

### Select extracted text within a pipeline

When you want an explicit choice among multiple extraction outputs, add a selection extractor step at the end of the pipeline.

```
python -m biblicus extract build --corpus corpora/demo \
  --step pass-through-text \
  --step metadata-text \
  --step select-text
```

Copy the `snapshot_id` from the JavaScript Object Notation output. Use it as `EXTRACTION_SNAPSHOT_ID` in the next command.

```
python -m biblicus build --corpus corpora/demo --backend sqlite-full-text-search \
  --config extraction_snapshot=pipeline:EXTRACTION_SNAPSHOT_ID
```

Extraction pipeline details: `docs/extraction.md`

### Portable Document Format extraction and retrieval

This example downloads a small set of public Portable Document Format files, extracts text, builds a local full text index, and runs a query.

```
rm -rf corpora/pdf_samples
python scripts/download_pdf_samples.py --corpus corpora/pdf_samples --force

python -m biblicus extract build --corpus corpora/pdf_samples --step pdf-text
```

Copy the `snapshot_id` from the JavaScript Object Notation output. Use it as `PDF_EXTRACTION_SNAPSHOT_ID` in the next command.

```
python -m biblicus build --corpus corpora/pdf_samples --backend sqlite-full-text-search --config extraction_snapshot=pipeline:PDF_EXTRACTION_SNAPSHOT_ID --config chunk_size=200 --config chunk_overlap=50 --config snippet_characters=120
python -m biblicus query --corpus corpora/pdf_samples --query "Dummy PDF file"
```

Retrieval details: `docs/retrieval.md`

### MarkItDown extraction demo (Python 3.10+)

MarkItDown requires Python 3.10 or higher. This example uses the `py311` conda environment to run the extractor over the mixed sample corpus.

```
conda run -n py311 python -m pip install -e . "markitdown[all]"
conda run -n py311 python scripts/download_mixed_samples.py --corpus corpora/markitdown_demo_py311 --force
conda run -n py311 python -m biblicus extract build --corpus corpora/markitdown_demo_py311 --step markitdown
```

### Mixed modality integration corpus

This example assembles a tiny mixed corpus with a Markdown note, a Hypertext Markup Language page, an image, a Portable Document Format file with extractable text, and a generated Portable Document Format file with no extractable text.
It also includes a downloaded Office Open Extensible Markup Language document to support catchall extraction experiments.

```
rm -rf corpora/mixed_samples
python scripts/download_mixed_samples.py --corpus corpora/mixed_samples --force
python -m biblicus list --corpus corpora/mixed_samples
```

### Image samples (for optical character recognition experiments)

This example downloads a tiny image corpus intended for optical character recognition experiments: one image that contains text and one that should not.

```
rm -rf corpora/image_samples
python scripts/download_image_samples.py --corpus corpora/image_samples --force
python -m biblicus list --corpus corpora/image_samples
```

To perform optical character recognition on the image items, install the optional dependency:

```
python -m pip install "biblicus[ocr]"
```

Then build an extraction snapshot:

```
python -m biblicus extract build --corpus corpora/image_samples --step ocr-rapidocr
```

### Optional: Unstructured as a last-resort extractor

The `unstructured` extractor is an optional dependency. It is intended as a last-resort extractor for non-text items.

Install the optional dependency:

```
python -m pip install "biblicus[unstructured]"
```

Then build an extraction snapshot:

```
python -m biblicus extract build --corpus corpora/pdf_samples --step unstructured
```

To see Unstructured handle a non-Portable-Document-Format format, use the mixed corpus demo, which includes a `.docx` sample:

```
rm -rf corpora/mixed_samples
python scripts/download_mixed_samples.py --corpus corpora/mixed_samples --force
python -m biblicus extract build --corpus corpora/mixed_samples --step unstructured
```

When you want to prefer one extractor over another for the same item types, order the steps and end with `select-text`:

```
python -m biblicus extract build --corpus corpora/pdf_samples \
  --step unstructured \
  --step pdf-text \
  --step select-text
```

### Optional: Speech to text for audio items

This example downloads a small set of public speech samples from Wikimedia Commons and uses extraction to derive text artifacts.
It also includes a generated Waveform Audio File Format silence clip for repeatable non-speech cases.

Download the integration corpus:

```
rm -rf corpora/audio_samples
python scripts/download_audio_samples.py --corpus corpora/audio_samples --force
python -m biblicus list --corpus corpora/audio_samples
```

If you only want a metadata-only baseline, extract `metadata-text`:

```
python -m biblicus extract build --corpus corpora/audio_samples --step metadata-text
```

For real speech to text transcription with the OpenAI backend, install the optional dependency and set an API key:

```
python -m pip install "biblicus[openai]"
mkdir -p .biblicus
printf "openai:\n  api_key: ...\n" > .biblicus/config.yml
python -m biblicus extract build --corpus corpora/audio_samples --step stt-openai
```

### Build and query the minimal backend

The scan backend is a minimal baseline that reads raw items directly.

```
python -m biblicus build --corpus corpora/demo --backend scan
python -m biblicus query --corpus corpora/demo --query "Hello"
```

Backend details: `docs/backends.md`

### Build and query the practical backend

The sqlite full text search backend builds a local index under the snapshot directory.

```
python -m biblicus build --corpus corpora/demo --backend sqlite-full-text-search --config extraction_snapshot=pipeline:EXTRACTION_SNAPSHOT_ID
python -m biblicus query --corpus corpora/demo --query "tiny"
```

Backend details: `docs/backends.md`

### Run the test suite and view coverage

```
python scripts/test.py
open reports/htmlcov/index.html
```

To include integration scenarios that download public test data at runtime:

```
python scripts/test.py --integration
```

Testing details: `docs/testing.md`

## Documentation map

- Corpus: `docs/corpus.md`
- Text extraction: `docs/extraction.md`
- Backends: `docs/backends.md`
- Testing: `docs/testing.md`
- Roadmap: `docs/roadmap.md`

For what to build next, see `docs/roadmap.md`.

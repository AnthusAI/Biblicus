# Local corpora for testing

This folder is the recommended place to create local corpora for manual testing and daily use.

- Everything here is ignored by Git, except this README file.
- Create one subfolder per corpus, such as `corpora/my-notes/`.

Example:

```bash
# from the Biblicus repository root
python3 -m biblicus init corpora/my-notes
python3 -m biblicus --corpus corpora/my-notes ingest --note "hello" --title "Test" --tag scratch
python3 -m biblicus --corpus corpora/my-notes list
python3 -m biblicus --corpus corpora/my-notes reindex
```

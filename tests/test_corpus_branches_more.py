from types import SimpleNamespace
from pathlib import Path

from biblicus import corpus


def test_corpus_latest_pointer_missing(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    # no latest.json should return None gracefully
    assert c.latest_extraction_snapshot_reference(extractor_id="pipeline") is None

from types import SimpleNamespace
from pathlib import Path

from biblicus import corpus


def test_corpus_latest_pointer_missing(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    # no latest.json should return None gracefully
    assert c.latest_extraction_snapshot(extractor_id="pipeline") is None


def test_corpus_rescan_skips_missing_snapshot(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    # create meta dir but no snapshots
    (tmp_path / "metadata").mkdir(exist_ok=True)
    c.rescan_snapshots()
    assert (tmp_path / "metadata" / "catalog.json").exists()


def test_corpus_purge_missing_snapshot(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    # nothing to purge should not raise
    c.purge_snapshot(extractor_id="pipeline", snapshot_id="missing")


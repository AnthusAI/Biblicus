"""
Command-line dependency planning tests for Biblicus.
"""

from __future__ import annotations

from argparse import Namespace

import pytest

from biblicus.cli import cmd_build, cmd_query
from biblicus.corpus import Corpus


def _init_corpus(tmp_path) -> Corpus:
    corpus = Corpus.init(tmp_path)
    corpus.ingest_note("Hello world", title="Test")
    return corpus


def _build_args_for_build(corpus: Corpus, **overrides) -> Namespace:
    data = {
        "corpus": str(corpus.root),
        "retriever": "scan",
        "configuration_name": "default",
        "configuration": None,
        "override": None,
        "auto_deps": False,
        "no_deps": False,
    }
    data.update(overrides)
    return Namespace(**data)


def _build_args_for_query(corpus: Corpus, **overrides) -> Namespace:
    data = {
        "corpus": str(corpus.root),
        "snapshot": None,
        "retriever": "scan",
        "query": "Hello?",
        "offset": 0,
        "max_total_items": 5,
        "maximum_total_characters": 2000,
        "max_items_per_source": 5,
        "reranker_id": None,
        "minimum_score": None,
        "auto_deps": False,
        "no_deps": False,
    }
    data.update(overrides)
    return Namespace(**data)


def test_cmd_build_auto_deps_creates_snapshots(tmp_path):
    """
    Auto dependency execution builds extraction and retrieval snapshots.
    """
    corpus = _init_corpus(tmp_path)
    arguments = _build_args_for_build(corpus, auto_deps=True)

    exit_code = cmd_build(arguments)

    assert exit_code == 0
    assert corpus.latest_snapshot_id is not None
    assert corpus.latest_extraction_snapshot_reference() is not None


def test_cmd_build_no_deps_raises_when_missing(tmp_path):
    """
    Build fails fast when dependencies are missing and --no-deps is set.
    """
    corpus = _init_corpus(tmp_path)
    arguments = _build_args_for_build(corpus, no_deps=True)

    with pytest.raises(ValueError, match="Dependencies missing for index"):
        cmd_build(arguments)


def test_cmd_query_auto_deps_builds_before_query(tmp_path, capsys):
    """
    Query auto-deps builds required snapshots when missing.
    """
    corpus = _init_corpus(tmp_path)
    arguments = _build_args_for_query(corpus, auto_deps=True)

    exit_code = cmd_query(arguments)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert corpus.latest_snapshot_id is not None
    assert captured.out.strip()


def test_cmd_query_no_deps_raises_when_missing(tmp_path):
    """
    Query fails fast when dependencies are missing and --no-deps is set.
    """
    corpus = _init_corpus(tmp_path)
    arguments = _build_args_for_query(corpus, no_deps=True)

    with pytest.raises(ValueError, match="Dependencies missing for query"):
        cmd_query(arguments)

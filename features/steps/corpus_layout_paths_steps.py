"""
Step definitions for corpus layout path accessors.
"""

from __future__ import annotations

from pathlib import Path

from behave import then, when

from biblicus.corpus import Corpus


def _corpus_root_for_layout(context, corpus_name: str) -> Path:
    return (context.workdir / corpus_name).resolve()


def _opened_corpus(context) -> Corpus:
    corpus = getattr(context, "layout_corpus", None)
    assert isinstance(corpus, Corpus), "Open the corpus as a Python object first."
    return corpus


@when('I open the corpus at "{corpus_name}" as a Python object')
def step_open_corpus_as_python_object(context, corpus_name: str) -> None:
    context.layout_corpus = Corpus.open(_corpus_root_for_layout(context, corpus_name))


@then('the corpus catalog path is "{relative_path}" under the corpus root')
def step_corpus_catalog_path_is(context, relative_path: str) -> None:
    corpus = _opened_corpus(context)
    assert corpus.catalog_path == corpus.root / relative_path, corpus.catalog_path


@then(
    'the corpus extracted text path for extractor "{extractor_id}", snapshot "{snapshot_id}" '
    'and item "{item_id}" is "{relative_path}" under the corpus root'
)
def step_corpus_extracted_text_path_is(
    context, extractor_id: str, snapshot_id: str, item_id: str, relative_path: str
) -> None:
    corpus = _opened_corpus(context)
    extracted_text_path = corpus.extracted_text_path(
        extractor_id=extractor_id, snapshot_id=snapshot_id, item_id=item_id
    )
    assert extracted_text_path == corpus.root / relative_path, extracted_text_path
    assert not extracted_text_path.exists()


@then(
    'the corpus graph snapshot manifest path for extractor "{extractor_id}" and snapshot '
    '"{snapshot_id}" is "{relative_path}" under the corpus root'
)
def step_corpus_graph_snapshot_manifest_path_is(
    context, extractor_id: str, snapshot_id: str, relative_path: str
) -> None:
    corpus = _opened_corpus(context)
    manifest_path = corpus.graph_snapshot_manifest_path(
        extractor_id=extractor_id, snapshot_id=snapshot_id
    )
    assert manifest_path == corpus.root / relative_path, manifest_path
    assert not manifest_path.exists()


@then("the corpus catalog path is a file")
def step_corpus_catalog_path_is_file(context) -> None:
    assert _opened_corpus(context).catalog_path.is_file()


@then(
    'the corpus extracted text path for the last ingested item in the latest "{extractor_id}" '
    'extraction snapshot contains "{expected_text}"'
)
def step_corpus_extracted_text_path_contains(
    context, extractor_id: str, expected_text: str
) -> None:
    corpus = _opened_corpus(context)
    extracted_text_path = corpus.extracted_text_path(
        extractor_id=extractor_id,
        snapshot_id=context.last_extraction_snapshot_id,
        item_id=context.last_ingest["id"],
    )
    assert extracted_text_path.is_file(), extracted_text_path
    assert expected_text in extracted_text_path.read_text(encoding="utf-8")


@then("the corpus graph snapshot manifest path for the last graph extraction snapshot is a file")
def step_corpus_graph_snapshot_manifest_path_is_file(context) -> None:
    corpus = _opened_corpus(context)
    manifest_path = corpus.graph_snapshot_manifest_path(
        extractor_id=context.last_graph_extractor_id,
        snapshot_id=context.last_graph_snapshot_id,
    )
    assert manifest_path.is_file(), manifest_path

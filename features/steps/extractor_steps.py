from __future__ import annotations

from typing import Any, Dict

from behave import then, when

from biblicus.corpus import Corpus
from biblicus.extractors.base import TextExtractor
from biblicus.models import CatalogItem
from biblicus.time import utc_now_iso


class _AbstractExtractorProbe(TextExtractor):
    extractor_id = "probe"

    def validate_config(self, config: Dict[str, Any]):
        return super().validate_config(config)

    def extract_text(self, *, corpus: Corpus, item: CatalogItem, config):
        return super().extract_text(corpus=corpus, item=item, config=config)


@when("I call the abstract extractor methods")
def step_call_abstract_extractor_methods(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus")
    probe = _AbstractExtractorProbe()
    context.extractor_validate_error = None
    context.extractor_extract_error = None
    try:
        probe.validate_config({})
    except Exception as exc:
        context.extractor_validate_error = exc
    item = CatalogItem(
        id="item",
        relpath="raw/item.txt",
        sha256="0" * 64,
        bytes=0,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        created_at=utc_now_iso(),
        source_uri=None,
    )
    try:
        probe.extract_text(corpus=corpus, item=item, config={})
    except Exception as exc:
        context.extractor_extract_error = exc


@then("the abstract extractor errors are raised")
def step_abstract_extractor_errors_raised(context) -> None:
    assert isinstance(context.extractor_validate_error, NotImplementedError)
    assert isinstance(context.extractor_extract_error, NotImplementedError)

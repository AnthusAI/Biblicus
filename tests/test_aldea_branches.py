from types import SimpleNamespace

import pytest

from biblicus.extractors.aldea_stt import AldeaSpeechToTextExtractor, AldeaSpeechToTextExtractorConfig
from biblicus.models import CatalogItem
from biblicus.corpus import Corpus


def test_aldea_extract_handles_missing_alternatives(monkeypatch, tmp_path):
    def fake_post(url, json=None, headers=None, timeout=None):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"results": {"channels": [{}]}},
        )

    monkeypatch.setattr("requests.post", fake_post)
    extractor = AldeaSpeechToTextExtractor()
    config = AldeaSpeechToTextExtractorConfig(api_key="k", language="en", url="http://example.com")
    item = CatalogItem(
        id="i",
        relpath="raw/a.wav",
        sha256="h",
        bytes=1,
        media_type="audio/wav",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://a",
    )
    corpus = Corpus(tmp_path)
    result = extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert result.text == ""

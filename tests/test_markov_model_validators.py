import pytest

from biblicus.analysis.models import (
    MarkovAnalysisSpanMarkupSegmentationConfig,
    LlmClientConfig,
)


def test_span_markup_chunk_overlap_requires_chunk_size():
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            client=LlmClientConfig(provider="mock"),
            prompt_template="tmpl",
            chunk_overlap_characters=10,
        )


def test_span_markup_chunk_overlap_must_be_smaller():
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            client=LlmClientConfig(provider="mock"),
            prompt_template="tmpl",
            chunk_characters=5,
            chunk_overlap_characters=6,
        )

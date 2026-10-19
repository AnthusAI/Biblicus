from __future__ import annotations

from behave import then, when


class _FakeConversionResult:
    text_content = "Transcript text long enough to be treated as real content."
    markdown = text_content
    title = "Video"


@when('I classify the source URL "{uri}" using a fake YouTube converter')
def step_extract_url_text_with_fake_youtube_converter(context, uri: str) -> None:
    import biblicus.url_text as url_text_module

    received_sources = []
    context.fake_youtube_converter_received = received_sources

    class FakeConverter:
        def convert(self, source, **_keyword_arguments):
            received_sources.append(source)
            return _FakeConversionResult()

    def fake_fetch(**kwargs):
        return {
            "ok": False,
            "body": b"",
            "content_type": None,
            "final_url": kwargs.get("uri"),
            "attempts": [],
            "error": {"code": "not_found", "message": "fixture not served"},
        }

    original_fetch = url_text_module._fetch_url_bytes
    original_builder = url_text_module._build_markitdown_converter
    url_text_module._fetch_url_bytes = fake_fetch
    url_text_module._build_markitdown_converter = FakeConverter
    try:
        context.url_text_result = url_text_module.extract_url_text(source_uri=uri)
    finally:
        url_text_module._fetch_url_bytes = original_fetch
        url_text_module._build_markitdown_converter = original_builder


@then('the URL text source kind is "{source_kind}"')
def step_url_source_kind(context, source_kind: str) -> None:
    assert context.url_text_result.get("source_kind") == source_kind


@then('the fake YouTube converter received "{canonical}"')
def step_fake_youtube_converter_received(context, canonical: str) -> None:
    assert context.fake_youtube_converter_received == [canonical]


@then('the URL text strategy is "{strategy}"')
def step_url_strategy(context, strategy: str) -> None:
    assert context.url_text_result.get("strategy") == strategy

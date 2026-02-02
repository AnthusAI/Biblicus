from behave import then, when

from biblicus.context_engine.compaction import CompactionRequest, build_compactor


def _normalize_value(value: str) -> str:
    return "" if value == "<empty>" else value


@when('I compact "{text}" with truncate compactor at {max_tokens:d} tokens')
def step_compact_truncate(context, text: str, max_tokens: int) -> None:
    compactor = build_compactor({"type": "truncate"})
    context.compacted_text = compactor.compact(
        CompactionRequest(text=_normalize_value(text), max_tokens=max_tokens)
    )


@when('I compact "{text}" with summary compactor at {max_tokens:d} tokens')
def step_compact_summary(context, text: str, max_tokens: int) -> None:
    compactor = build_compactor({"type": "summary"})
    context.compacted_text = compactor.compact(
        CompactionRequest(text=_normalize_value(text), max_tokens=max_tokens)
    )


@then('the compacted text equals "{expected}"')
def step_compacted_equals(context, expected: str) -> None:
    assert context.compacted_text == _normalize_value(expected)

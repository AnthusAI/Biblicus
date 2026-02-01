from __future__ import annotations

from typing import List

from behave import then, when

from biblicus.analysis.markov import _add_boundary_segments
from biblicus.analysis.models import MarkovAnalysisSegment


@when("I add boundary segments to a two-segment item")
def step_add_boundary_segments(context) -> None:
    segments: List[MarkovAnalysisSegment] = [
        MarkovAnalysisSegment(item_id="item-1", segment_index=1, text="Hello there."),
        MarkovAnalysisSegment(item_id="item-1", segment_index=2, text="Thanks, goodbye."),
    ]
    context.last_segments = _add_boundary_segments(segments=segments)


@then('the first segment equals "{text}"')
def step_first_segment_equals(context, text: str) -> None:
    segments = context.last_segments
    assert segments
    assert segments[0].text == text


@then('the last segment equals "{text}"')
def step_last_segment_equals(context, text: str) -> None:
    segments = context.last_segments
    assert segments
    assert segments[-1].text == text


@then("the boundary segments are added")
def step_boundary_segments_added(context) -> None:
    segments = context.last_segments
    assert segments
    assert len(segments) == 4

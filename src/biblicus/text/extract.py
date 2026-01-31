"""
Agentic text extraction using virtual file edits.
"""

from __future__ import annotations

import re
from typing import List

from .models import TextExtractRequest, TextExtractResult, TextExtractSpan
from .tool_loop import run_tool_loop


def apply_text_extract(request: TextExtractRequest) -> TextExtractResult:
    """
    Apply text extraction using a language model.

    :param request: Text extract request.
    :type request: TextExtractRequest
    :return: Text extract result.
    :rtype: TextExtractResult
    :raises ValueError: If model output is invalid or text is modified.
    """
    warnings: List[str] = []
    result = run_tool_loop(
        text=request.text,
        client=request.client,
        system_prompt=request.system_prompt,
        prompt_template=request.prompt_template,
        max_rounds=request.max_rounds,
        max_edits_per_round=request.max_edits_per_round,
        apply_str_replace=_apply_extract_replace,
    )
    if not result.done:
        if result.last_error:
            raise ValueError(f"Text extract failed: {result.last_error}")
        warnings.append("Text extract reached max rounds without done=true")
    if result.text == request.text:
        if result.last_error:
            raise ValueError(result.last_error)
        raise ValueError("Text extract produced no spans")
    _validate_preserved_text(original=request.text, marked_up=result.text)
    spans = _extract_spans(marked_up_text=result.text)
    return TextExtractResult(marked_up_text=result.text, spans=spans, warnings=warnings)


def _apply_extract_replace(text: str, old_str: str, new_str: str) -> str:
    occurrences = text.count(old_str)
    if occurrences == 0:
        raise ValueError("Text extract replacement old_str not found")
    if occurrences > 1:
        raise ValueError("Text extract replacement old_str is not unique")
    _validate_replace_text(old_str, new_str)
    return text.replace(old_str, new_str, 1)


def _validate_replace_text(old_str: str, new_str: str) -> None:
    if _strip_span_tags(old_str) != _strip_span_tags(new_str):
        raise ValueError("Text extract replacements may only insert span tags")


def _validate_preserved_text(*, original: str, marked_up: str) -> None:
    if _strip_span_tags(marked_up) != original:
        raise ValueError("Text extract edits modified the source text")


def _strip_span_tags(text: str) -> str:
    return text.replace("<span>", "").replace("</span>", "")


def _extract_spans(*, marked_up_text: str) -> List[TextExtractSpan]:
    open_tag = "<span>"
    close_tag = "</span>"
    tag_pattern = re.compile(re.escape(open_tag) + "|" + re.escape(close_tag))
    spans: List[TextExtractSpan] = []
    cursor = 0
    original_index = 0
    span_start = None
    span_text = ""

    for match in tag_pattern.finditer(marked_up_text):
        chunk = marked_up_text[cursor : match.start()]
        if chunk:
            if span_start is not None:
                span_text += chunk
            original_index += len(chunk)
        tag = match.group(0)
        if tag == open_tag:
            if span_start is not None:
                raise ValueError("Text extract contains nested spans")
            span_start = original_index
            span_text = ""
        else:
            if span_start is None:
                raise ValueError("Text extract contains an unmatched closing tag")
            span_end = original_index
            spans.append(
                TextExtractSpan(
                    index=len(spans) + 1,
                    start_char=span_start,
                    end_char=span_end,
                    text=span_text,
                )
            )
            span_start = None
            span_text = ""
        cursor = match.end()

    tail = marked_up_text[cursor:]
    if tail:
        if span_start is not None:
            span_text += tail
        original_index += len(tail)

    if span_start is not None:
        raise ValueError("Text extract contains an unclosed span")

    return spans

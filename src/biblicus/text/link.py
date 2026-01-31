"""
Agentic text linking using virtual file edits.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from jinja2 import Environment, StrictUndefined

from .markup import (
    TextAnnotatedSpan,
    build_span_context_section,
    parse_span_markup,
    strip_span_tags,
)
from .models import TextLinkRequest, TextLinkResult
from .tool_loop import run_tool_loop

DEFAULT_LINK_ID_PREFIX = "link_"


def apply_text_link(request: TextLinkRequest) -> TextLinkResult:
    """
    Apply text linking using a language model.

    :param request: Text link request.
    :type request: TextLinkRequest
    :return: Text link result.
    :rtype: TextLinkResult
    :raises ValueError: If model output is invalid or text is modified.
    """
    warnings: List[str] = []
    system_prompt = _render_system_prompt(
        request.system_prompt,
        id_prefix=request.id_prefix,
    )

    result = run_tool_loop(
        text=request.text,
        client=request.client,
        system_prompt=system_prompt,
        prompt_template=request.prompt_template,
        max_rounds=request.max_rounds,
        max_edits_per_round=request.max_edits_per_round,
        apply_str_replace=_apply_link_replace,
        validate_text=lambda current_text: _validate_link_markup(
            current_text, request.id_prefix
        ),
        build_retry_message=lambda errors, current_text: _build_retry_message(
            errors, current_text, request.id_prefix
        ),
    )

    if not result.done:
        if result.last_error:
            raise ValueError(f"Text link failed: {result.last_error}")
        warnings.append("Text link reached max rounds without done=true")

    if result.text == request.text:
        if result.last_error:
            raise ValueError(result.last_error)
        raise ValueError("Text link produced no spans")

    _validate_preserved_text(original=request.text, marked_up=result.text)
    spans = parse_span_markup(result.text)
    errors = _validate_link_spans(spans, request.id_prefix)
    if errors:
        raise ValueError("; ".join(errors))

    return TextLinkResult(marked_up_text=result.text, spans=spans, warnings=warnings)


def _render_system_prompt(template: str, *, id_prefix: str) -> str:
    env = Environment(undefined=StrictUndefined)
    rendered = env.from_string(template).render(
        id_prefix=id_prefix,
    )
    return rendered


def _apply_link_replace(text: str, old_str: str, new_str: str) -> str:
    occurrences = text.count(old_str)
    if occurrences == 0:
        raise ValueError("Text link replacement old_str not found")
    if occurrences > 1:
        raise ValueError("Text link replacement old_str is not unique")
    _validate_replace_text(old_str, new_str)
    return text.replace(old_str, new_str, 1)


def _validate_replace_text(old_str: str, new_str: str) -> None:
    if strip_span_tags(old_str) != strip_span_tags(new_str):
        raise ValueError("Text link replacements may only insert span tags")


def _validate_preserved_text(*, original: str, marked_up: str) -> None:
    if strip_span_tags(marked_up) != original:
        raise ValueError("Text link edits modified the source text")


def _validate_link_markup(marked_up_text: str, id_prefix: str) -> List[str]:
    try:
        spans = parse_span_markup(marked_up_text)
    except ValueError as exc:
        return [str(exc)]
    return _validate_link_spans(spans, id_prefix)


def _validate_link_spans(
    spans: Iterable[TextAnnotatedSpan], id_prefix: str
) -> List[str]:
    errors: List[str] = []
    seen_ids: List[str] = []
    for span in spans:
        if len(span.attributes) != 1:
            errors.append(f"Span {span.index} must include exactly one attribute")
            continue
        name, value = next(iter(span.attributes.items()))
        if value.strip() == "":
            errors.append(f"Span {span.index} has an empty value for attribute '{name}'")
            continue
        if name == "id":
            if not value.startswith(id_prefix):
                errors.append(
                    f"Span {span.index} id '{value}' must start with '{id_prefix}'"
                )
            if value in seen_ids:
                errors.append(f"Span {span.index} uses duplicate id '{value}'")
            seen_ids.append(value)
        elif name == "ref":
            if value not in seen_ids:
                errors.append(
                    f"Span {span.index} ref '{value}' does not match a previous id"
                )
        else:
            errors.append(
                f"Span {span.index} uses attribute '{name}' but only 'id' or 'ref' are allowed"
            )
    return errors


def _build_retry_message(errors: Sequence[str], current_text: str, id_prefix: str) -> str:
    error_lines = "\n".join(f"- {error}" for error in errors)
    context_section = build_span_context_section(current_text, errors)
    return (
        "Your last edit did not validate.\n"
        "Issues:\n"
        f"{error_lines}\n\n"
        f"{context_section}"
        "Please fix the markup using str_replace. Use id for first mentions and ref for repeats. "
        f"Ids must start with '{id_prefix}'. Try again.\n"
        "Current text:\n"
        f"---\n{current_text}\n---"
    )

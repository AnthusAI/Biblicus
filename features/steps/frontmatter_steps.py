from __future__ import annotations

from behave import then, when

from biblicus.frontmatter import (
    parse_front_matter,
    render_front_matter,
    split_markdown_front_matter,
)


@when('I render front matter with empty metadata and body "{body}"')
def step_render_empty_frontmatter(context, body: str) -> None:
    context.rendered_markdown = render_front_matter({}, body)


@then('the rendered markdown equals "{expected}"')
def step_rendered_equals(context, expected: str) -> None:
    assert context.rendered_markdown == expected


@when("I parse front matter from text without a closing fence")
def step_parse_no_closing_fence(context) -> None:
    text = "---\ntitle: T\nbody: nope\n"
    context.parsed_doc = parse_front_matter(text)


@then("the parsed metadata is empty")
def step_parsed_metadata_empty(context) -> None:
    assert context.parsed_doc.metadata == {}


@then('the parsed body starts with "---"')
def step_parsed_body_starts_with(context) -> None:
    assert context.parsed_doc.body.startswith("---")


@when('I split front matter from markdown with title "{title}" and body "{body}"')
def step_split_frontmatter(context, title: str, body: str) -> None:
    text = render_front_matter({"title": title}, body)
    meta, out_body = split_markdown_front_matter(text)
    context.split_meta = meta
    context.split_body = out_body


@then('the split metadata includes title "{title}"')
def step_split_meta_title(context, title: str) -> None:
    assert context.split_meta.get("title") == title


@then('the split body equals "{body}"')
def step_split_body_equals(context, body: str) -> None:
    assert context.split_body == body

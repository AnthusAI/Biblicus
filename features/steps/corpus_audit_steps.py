from __future__ import annotations

import json

from behave import then, when

from features.environment import run_biblicus
from features.steps.cli_steps import _corpus_path


@when('I audit corpus "{corpus_name}" as markdown')
def step_audit_corpus_markdown(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["corpus", "audit", "--corpus", str(corpus), "--format", "markdown"],
    )
    assert result.returncode == 0, result.stderr


@when('I audit corpus "{corpus_name}" as JSON')
def step_audit_corpus_json(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["corpus", "audit", "--corpus", str(corpus), "--format", "json"],
    )
    assert result.returncode == 0, result.stderr
    context.last_corpus_audit = json.loads(result.stdout)


@when(
    'I audit corpus "{corpus_name}" as JSON with required tag "{required_tag}" and forbidden tag "{forbidden_tag}"'
)
def step_audit_corpus_json_with_tag_policy(
    context, corpus_name: str, required_tag: str, forbidden_tag: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        [
            "corpus",
            "audit",
            "--corpus",
            str(corpus),
            "--format",
            "json",
            "--required-tag",
            required_tag,
            "--forbid-tag",
            forbidden_tag,
        ],
    )
    assert result.returncode == 0, result.stderr
    context.last_corpus_audit = json.loads(result.stdout)


@when('I audit corpus "{corpus_name}" as JSON using the last extraction snapshot')
def step_audit_corpus_json_with_last_extraction(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    extractor_id = getattr(context, "last_extractor_id", None)
    snapshot_id = getattr(context, "last_extraction_snapshot_id", None)
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    result = run_biblicus(
        context,
        [
            "corpus",
            "audit",
            "--corpus",
            str(corpus),
            "--format",
            "json",
            "--extraction-snapshot",
            f"{extractor_id}:{snapshot_id}",
        ],
    )
    assert result.returncode == 0, result.stderr
    context.last_corpus_audit = json.loads(result.stdout)


@then('the corpus audit issues include code "{code}" for title "{title}"')
def step_corpus_audit_issues_include_code_for_title(context, code: str, title: str) -> None:
    audit = getattr(context, "last_corpus_audit", None)
    assert isinstance(audit, dict)
    issues = audit.get("issues") or []
    assert any(
        issue.get("code") == code and issue.get("title") == title for issue in issues
    ), issues


@then('the corpus audit duplicates include key type "{key_type}" and key "{key}"')
def step_corpus_audit_duplicates_include_key(context, key_type: str, key: str) -> None:
    audit = getattr(context, "last_corpus_audit", None)
    assert isinstance(audit, dict)
    duplicates = audit.get("duplicates") or []
    assert any(
        group.get("key_type") == key_type and group.get("key") == key for group in duplicates
    ), duplicates


@then("the corpus audit extraction is current with missing item count {count:d}")
def step_corpus_audit_extraction_current(context, count: int) -> None:
    audit = getattr(context, "last_corpus_audit", None)
    assert isinstance(audit, dict)
    extraction = audit.get("extraction")
    assert isinstance(extraction, dict)
    assert extraction.get("stale_catalog") is False
    assert extraction.get("missing_item_count") == count


@then("the corpus audit extraction is stale with missing item count {count:d}")
def step_corpus_audit_extraction_stale(context, count: int) -> None:
    audit = getattr(context, "last_corpus_audit", None)
    assert isinstance(audit, dict)
    extraction = audit.get("extraction")
    assert isinstance(extraction, dict)
    assert extraction.get("stale_catalog") is True
    assert extraction.get("missing_item_count") == count

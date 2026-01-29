from __future__ import annotations

from pathlib import Path

from behave import given, then, when

from biblicus.knowledge_base import KnowledgeBase


@given('a folder "{folder}" exists')
def given_folder_exists(context, folder: str) -> None:
    root = Path(context.workdir) / folder
    root.mkdir(parents=True, exist_ok=True)
    context.knowledge_base_folder = root


@given('a folder "{folder}" exists with text files:')
def given_folder_exists_with_text_files(context, folder: str) -> None:
    root = Path(context.workdir) / folder
    root.mkdir(parents=True, exist_ok=True)
    for row in context.table:
        filename = row["filename"]
        contents = row["contents"]
        path = root / filename
        path.write_text(contents, encoding="utf-8")
    context.knowledge_base_folder = root


@given('a file "{filename}" exists with contents "{contents}"')
def given_file_exists_with_contents(context, filename: str, contents: str) -> None:
    path = Path(context.workdir) / filename
    path.write_text(contents, encoding="utf-8")
    context.knowledge_base_file = path


@when('I create a knowledge base from folder "{folder}" only')
def when_create_knowledge_base_from_folder(context, folder: str) -> None:
    root = Path(context.workdir) / folder
    context.knowledge_base = KnowledgeBase.from_folder(root)


@when('I create a knowledge base from folder "{folder}" using corpus root "{corpus_root}"')
def when_create_knowledge_base_from_folder_with_corpus_root(
    context, folder: str, corpus_root: str
) -> None:
    root = Path(context.workdir) / folder
    corpus_root_path = Path(context.workdir) / corpus_root
    context.knowledge_base = KnowledgeBase.from_folder(root, corpus_root=corpus_root_path)


@when('I attempt to create a knowledge base from folder "{folder}"')
def when_attempt_create_knowledge_base_from_folder(context, folder: str) -> None:
    root = Path(context.workdir) / folder
    try:
        KnowledgeBase.from_folder(root)
    except (FileNotFoundError, NotADirectoryError) as exc:
        context.knowledge_base_error = exc


@then('the knowledge base error includes "{text}"')
def then_knowledge_base_error_includes(context, text: str) -> None:
    error = context.knowledge_base_error
    assert text in str(error)


@when('I query the knowledge base for "{query_text}"')
def when_query_knowledge_base(context, query_text: str) -> None:
    context.knowledge_base_result = context.knowledge_base.query(query_text)


@when("I build a context pack from the knowledge base query with token budget {max_tokens:d}")
def when_build_context_pack_from_knowledge_base_query(context, max_tokens: int) -> None:
    context.context_pack = context.knowledge_base.context_pack(
        context.knowledge_base_result,
        max_tokens=max_tokens,
    )


@when("I build a context pack from the knowledge base query without a token budget")
def when_build_context_pack_from_knowledge_base_query_without_budget(context) -> None:
    context.context_pack = context.knowledge_base.context_pack(
        context.knowledge_base_result,
    )


@then('the knowledge base returns evidence that includes "{text}"')
def then_knowledge_base_returns_evidence_that_includes(context, text: str) -> None:
    evidence_items = context.knowledge_base_result.evidence
    evidence_texts = [item.text or "" for item in evidence_items]
    assert any(text in evidence_text for evidence_text in evidence_texts)

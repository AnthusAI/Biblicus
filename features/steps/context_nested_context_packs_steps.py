from behave import given, then, when
from context_engine_registry import RegistryBuilder

from biblicus.context import ContextPack, ContextPackBlock
from biblicus.context_engine import ContextAssembler


@given("a nested Context pack that includes another context pack")
def step_nested_context_pack_with_context(context):
    builder = RegistryBuilder()
    builder.register_corpus(
        "wikitext",
        {"source": "wikitext2", "split": "train", "maximum_cache_total_items": 2000},
    )
    builder.register_retriever(
        "wikitext_search",
        {
            "corpus": "wikitext",
            "query": "Valkyria Chronicles III",
            "limit": 5,
            "maximum_total_characters": 800,
        },
    )
    builder.register_context(
        "nested_pack",
        {
            "messages": [
                {"type": "system", "content": "Nested context"},
                {"type": "context", "name": "wikitext_search"},
            ]
        },
    )
    builder.register_context(
        "support_context",
        {
            "messages": [
                {"type": "context", "name": "nested_pack"},
                {"type": "user", "content": "Question"},
            ]
        },
    )
    context.registry = builder.registry
    context.context_name = "support_context"


@when("I assemble the outer Context")
def step_assemble_outer_context(context):
    def fake_retrieve(request):
        text = "Nested snippet"
        return ContextPack(
            text=text,
            evidence_count=1,
            blocks=[ContextPackBlock(evidence_item_id="fake-1", text=text, metadata=None)],
        )

    assembler = ContextAssembler(
        context.registry.contexts,
        retriever_registry=context.registry.retrievers,
        corpus_registry=context.registry.corpora,
    )
    context.result = assembler.assemble(
        context_name=context.context_name,
        base_system_prompt="",
        history_messages=[],
        user_message="",
        template_context={"input": {}, "context": {}},
        retriever_override=fake_retrieve,
    )


@then("the nested pack should include the composed context content")
def step_nested_pack_composed(context):
    assert "Nested context" in context.result.system_prompt
    assert "Nested snippet" in context.result.system_prompt

# Context Engine

The Context Engine is the Biblicus SDK for assembling elastic, budget-aware prompt contexts. It lets AI engineers describe *what* should be in an LLM request while Biblicus handles *how* to fit it into a budgeted context window.

It turns a high-level plan into:

- a system prompt
- a history message list
- a user message

The Context Engine can **compact** content when it is too large and **expand** retriever packs by paginating with `offset` and `limit`.

> “Context assembly is the most failure-prone part of agent engineering. Engineers need a reliable way to fit knowledge into limited context windows without hand-writing brittle logic.”

## Why Context Engine?

Context Engine provides a first-class, testable, and reusable context assembly surface. It is designed to be the shared foundation for both Python applications and Tactus procedures.

- **Composable Context plans**: Mix system/user messages, nested contexts, and retriever packs.
- **Budget-aware compaction**: Use pluggable compactor strategies.
- **Budget-aware expansion**: Use retriever pagination (`offset` + `limit`) to fill remaining budget.
- **Deterministic assembly**: Produce a predictable message history for model calls.

## Core Concepts

- **ContextDeclaration**: The plan describing which messages and packs to assemble.
- **ContextPolicySpec**: Budgeting, compaction, and expansion policy.
- **ContextAssembler**: The assembly engine that renders a ContextDeclaration.
- **ContextRetrieverRequest**: The request payload passed into retriever callables.

## Basic Usage

```python
from biblicus.context_engine import ContextAssembler, ContextDeclaration

context_spec = ContextDeclaration(
    name="support",
    messages=[
        {"type": "system", "content": "You are a support agent."},
        {"type": "user", "content": "Question: {input.question}"},
    ],
)

assembler = ContextAssembler({"support": context_spec})
result = assembler.assemble(
    context_name="support",
    base_system_prompt="",
    history_messages=[],
    user_message="",
    template_context={"input": {"question": "Where is my order?"}, "context": {}},
)

print(result.system_prompt)
print(result.user_message)
```

## Retriever Packs

Retriever packs are inserted with a `context` directive. You provide a retriever callable that
accepts a `ContextRetrieverRequest` and returns a `ContextPack`.

```python
from biblicus.context import ContextPack, ContextPackBlock
from biblicus.context_engine import ContextAssembler, ContextDeclaration, ContextRetrieverRequest


def fake_retrieve(request: ContextRetrieverRequest) -> ContextPack:
    text = "Evidence chunk"
    return ContextPack(
        text=text,
        evidence_count=1,
        blocks=[ContextPackBlock(evidence_item_id="demo-1", text=text, metadata=None)],
    )

context_spec = ContextDeclaration(
    name="support",
    policy={
        "input_budget": {"max_tokens": 10},
        "pack_budget": {"default_ratio": 1.0},
    },
    messages=[
        {"type": "system", "content": "Use this context."},
        {"type": "context", "name": "kb_search"},
        {"type": "user", "content": "Question"},
    ],
)

retriever_spec = type("RetrieverSpec", (), {"config": {"query": "demo", "limit": 3}})()

assembler = ContextAssembler(
    {"support": context_spec},
    retriever_registry={"kb_search": retriever_spec},
)
result = assembler.assemble(
    context_name="support",
    base_system_prompt="",
    history_messages=[],
    user_message="",
    template_context={"input": {}, "context": {}},
    retriever_override=fake_retrieve,
)
```

## Expansion and Pagination

Enable expansion in the policy to paginate retrievers when packs are under budget.

```python
policy = {
    "input_budget": {"max_tokens": 40},
    "pack_budget": {"default_ratio": 0.5},
    "expansion": {"max_pages": 3, "min_fill_ratio": 1.0},
}
```

The Context Engine will issue additional retrieval requests with increasing `offset` until the
pack budget is satisfied or no more results are returned.

## Compaction Strategies

When overflow is set to `compact`, the Context Engine compacts content with a pluggable compactor.

```python
policy = {
    "input_budget": {"max_tokens": 10},
    "overflow": "compact",
    "compactor": {"type": "truncate"},
}
```

Custom compactors can be registered via `compactor_registry`.

## FAQ

### What does “elastic” mean?

Elastic means the Context Engine can **contract** (compact) or **expand** (paginate) retrieval output depending on the current token budget. When a pack is too large it compacts; when it is too small and pagination is available, it can fetch additional pages.

### How is pagination used?

Retrievers accept `offset` and `limit`. The Context Engine uses those to request additional pages until a target budget is met or no more results are available.

### Does this replace Context packs?

No. Context packs are still derived from retrieval evidence. The Context Engine composes those packs into model messages and manages how they are sized and placed.

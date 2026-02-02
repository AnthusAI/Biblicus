# PR-FAQ: Elastic Context Engine

## Press Release

Today we are introducing the Biblicus **Context Engine**, a public Python SDK that assembles elastic, budget-aware model contexts from composable inputs. The Context Engine lets AI engineers describe *what* should be in an LLM request while Biblicus handles *how* to fit it into a budgeted context window. It can compact or expand retrieval packs, paginate retrievers on demand, and produce a deterministic message history for model calls.

The Context Engine is the shared foundation for both Python applications and Tactus procedures. Tactus now builds its Context primitive on top of Biblicus, so improvements to budgeting, compaction, pagination, and message assembly automatically benefit both ecosystems.

Key capabilities:

- **Composable Context plans** that mix system/user messages, nested contexts, and retriever packs.
- **Budget-aware compaction** using pluggable compactor strategies.
- **Budget-aware expansion** via retriever pagination using `offset` + `limit`.
- **Deterministic assembly** into system prompts, history, and user messages.
- **Public SDK** with Pydantic-first validation and clear, testable policies.

The result is a single, elegant Context abstraction that supports both high-level defaults and expert-level control over message placement and retrieval behavior.

## FAQ

**Q: What problem does this solve?**
A: Context assembly is the most failure-prone part of agent engineering. Engineers need a reliable way to fit knowledge into limited context windows without hand-writing brittle logic. The Context Engine provides a first-class, testable, and reusable context assembly surface.

**Q: What does “elastic” mean?**
A: Elastic means the Context Engine can **contract** (compact) or **expand** (paginate) retrieval output depending on the current token budget. When a pack is too large it compacts; when it is too small and pagination is available, it can fetch additional pages.

**Q: How is pagination used?**
A: Retrievers accept `offset` and `limit`. The Context Engine uses those to request additional pages until a target budget is met or no more results are available.

**Q: Does this replace Context packs?**
A: No. Context packs are still derived from retrieval evidence. The Context Engine composes those packs into model messages and manages how they are sized and placed.

**Q: How does this integrate with Tactus?**
A: Tactus Context declarations now delegate to the Biblicus Context Engine. Tactus provides DSL configuration and the runtime passes registry values into the Biblicus SDK.

**Q: Is this configurable?**
A: Yes. Policies control input budgets, pack budgets, compaction strategy, pagination limits, and message assembly. Engineers can also implement custom retrievers and compactors.

**Q: Is this backwards compatible?**
A: No. This is a first-class, unified interface. We intentionally remove legacy paths to keep the system clear and maintainable.

**Q: How is correctness verified?**
A: The behavior is specified in BDD scenarios that cover compaction, pagination, nesting, and message assembly. Coverage is enforced at 100%.

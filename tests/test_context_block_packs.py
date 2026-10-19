import importlib.util
import pathlib
import sys
import types


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "biblicus"
MODULE_PATH = PACKAGE_ROOT / "context.py"
package = types.ModuleType("biblicus")
package.__path__ = [str(PACKAGE_ROOT)]
sys.modules.setdefault("biblicus", package)

SPEC = importlib.util.spec_from_file_location("biblicus.context", MODULE_PATH)
biblicus_context = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = biblicus_context
SPEC.loader.exec_module(biblicus_context)

ContextBlock = biblicus_context.ContextBlock
ContextBlockBuildRequest = biblicus_context.ContextBlockBuildRequest
ContextSectionBudget = biblicus_context.ContextSectionBudget
build_context_pack_from_blocks = biblicus_context.build_context_pack_from_blocks


def test_build_context_pack_from_blocks_enforces_section_budget_before_overall_budget():
    result = build_context_pack_from_blocks(
        ContextBlockBuildRequest(
            blocks=[
                ContextBlock(block_id="doctrine-1", section="doctrine", text="mission policy", required=True),
                ContextBlock(block_id="memory-1", section="desk_memory", text="recent one"),
                ContextBlock(block_id="memory-2", section="desk_memory", text="recent two"),
            ],
            max_tokens=5,
            section_budgets=[
                ContextSectionBudget(section="doctrine", share=0.4),
                ContextSectionBudget(section="desk_memory", share=0.4),
            ],
        )
    )

    assert [block.block_id for block in result.included_blocks] == ["doctrine-1", "memory-1"]
    assert [block.block_id for block in result.dropped_blocks] == ["memory-2"]
    assert result.section_token_counts["doctrine"] == 2
    assert result.section_token_counts["desk_memory"] == 2


def test_build_context_pack_from_blocks_preserves_required_blocks_when_budget_is_tight():
    result = build_context_pack_from_blocks(
        ContextBlockBuildRequest(
            blocks=[
                ContextBlock(block_id="doctrine-1", section="doctrine", text="editorial mission", required=True),
                ContextBlock(block_id="doctrine-2", section="doctrine", text="desk policy", required=True),
                ContextBlock(block_id="optional-1", section="desk_memory", text="recent summary"),
            ],
            max_tokens=2,
        )
    )

    assert [block.block_id for block in result.included_blocks] == ["doctrine-1", "doctrine-2"]
    assert [block.block_id for block in result.dropped_blocks] == ["optional-1"]
    assert result.total_tokens == 4

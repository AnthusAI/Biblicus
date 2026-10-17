"""
Typed function for the ``context-pack build-blocks`` command.
"""

from __future__ import annotations

from ..context import (
    ContextBlockBuildRequest,
    ContextBlockBuildResult,
    build_context_pack_from_blocks,
)

ContextPackBuildBlocksRequest = ContextBlockBuildRequest
ContextPackBuildBlocksResponse = ContextBlockBuildResult


def context_pack_build_blocks(
    request: ContextPackBuildBlocksRequest,
) -> ContextPackBuildBlocksResponse:
    """
    Build a context pack from ordered context blocks.

    :param request: Validated block build request.
    :type request: ContextBlockBuildRequest
    :return: Built context pack with per-block accounting.
    :rtype: ContextBlockBuildResult
    """
    return build_context_pack_from_blocks(request)

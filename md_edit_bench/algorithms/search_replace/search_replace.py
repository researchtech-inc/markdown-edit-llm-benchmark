"""Search/replace algorithm - LLM outputs search/replace blocks (Aider-style)."""

from __future__ import annotations

import re

from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class SearchReplaceError(Exception):
    """Raised when a search/replace block cannot be applied safely."""


def parse_blocks(blocks_text: str) -> list[tuple[str, str]]:
    """Parse search/replace blocks from LLM output."""
    pattern = r"<{5,9} SEARCH\n(.*?)\n={5,9}\n(.*?)\n>{5,9} REPLACE"
    blocks: list[tuple[str, str]] = re.findall(pattern, blocks_text, re.DOTALL)

    if not blocks:
        pattern = r"<{5,9}\n(.*?)\n={5,9}\n(.*?)\n>{5,9}"
        blocks = re.findall(pattern, blocks_text, re.DOTALL)

    # Clean prompt artifacts from each block
    return [clean_search_replace_block(search, replace) for search, replace in blocks]


def apply_search_replace(original: str, blocks_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Parse and apply search/replace blocks using fuzzy matching on evolving document.

    Uses replace_most_similar_chunk for robust matching that handles:
    - Exact matches (preferred)
    - Whitespace differences
    - Minor text variations (80% similarity threshold)

    Applies blocks sequentially to evolving document state, allowing later blocks
    to reference text created by earlier blocks.

    Returns (result, failed_blocks) tuple where failed_blocks contains
    (block_number, search_text, replace_text) for blocks that couldn't be applied.
    Raises SearchReplaceError only for unrecoverable errors (no blocks, empty search).
    """
    blocks = parse_blocks(blocks_text)

    if not blocks:
        raise SearchReplaceError("No valid search/replace blocks found")

    result = original
    failed_blocks: list[tuple[int, str, str]] = []
    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            raise SearchReplaceError(f"Block {i}: empty search text")

        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            failed_blocks.append((i, search, replace))
        else:
            result = new_result

    return result, failed_blocks


def format_failed_blocks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed blocks for the retry prompt."""
    parts: list[str] = []
    for block_num, search, replace in failed:
        parts.append(f"Block {block_num}:")
        parts.append(f"SEARCH:\n{search}")
        parts.append(f"REPLACE:\n{replace}")
        parts.append("")
    return "\n".join(parts)


class SearchReplaceAlgorithm(Algorithm):
    """LLM outputs search/replace blocks (Aider-style), then parsed and applied."""

    name = "search_replace"
    description = "LLM outputs search/replace blocks, then parsed and applied"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        blocks_text, usage = await call_llm(model, user_prompt, system_prompt)

        try:
            result, failed_blocks = apply_search_replace(initial, blocks_text)
        except SearchReplaceError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

        if not failed_blocks:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )

        # Pass 2: Retry failed blocks with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_blocks=format_failed_blocks(failed_blocks),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        try:
            retry_result, retry_failed = apply_search_replace(result, retry_output)
            result = retry_result
        except SearchReplaceError:
            # Retry produced no valid blocks - all original failures become warnings
            warnings = [
                f"Block {block_num}: failed and retry produced no fix"
                for block_num, _search, _replace in failed_blocks
            ]
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Track unrecovered blocks
        warnings: list[str] = []
        if retry_failed:
            original_block_nums = [b[0] for b in failed_blocks]
            warnings.append(
                f"{len(retry_failed)} block(s) unrecovered after retry "
                f"(original failures: {original_block_nums})"
            )

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

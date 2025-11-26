"""Aider diff-fenced algorithm - filename INSIDE code fence for Gemini models."""

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


class DiffFencedError(Exception):
    """Raised when diff-fenced blocks cannot be parsed or applied."""


def parse_diff_fenced_blocks(content: str) -> list[tuple[str, str]]:
    """Parse diff-fenced blocks from LLM output.

    Returns list of (search, replace) tuples.
    """
    blocks: list[tuple[str, str]] = []
    lines = content.splitlines(keepends=True)
    i = 0

    head_pattern = re.compile(r"^<{5,9} SEARCH>?\s*$")
    divider_pattern = re.compile(r"^={5,9}\s*$")
    updated_pattern = re.compile(r"^>{5,9} REPLACE\s*$")
    fence_pattern = re.compile(r"^```")

    while i < len(lines):
        line = lines[i]

        # Look for opening fence (```markdown or similar)
        if fence_pattern.match(line.strip()):
            i += 1

            # Skip the filename line (should be next)
            if i < len(lines):
                i += 1

            # Now look for SEARCH block
            while i < len(lines):
                if head_pattern.match(lines[i].strip()):
                    # Found SEARCH marker
                    search_lines: list[str] = []
                    i += 1

                    # Collect search content until divider
                    while i < len(lines) and not divider_pattern.match(lines[i].strip()):
                        search_lines.append(lines[i])
                        i += 1

                    if i >= len(lines):
                        break

                    # Skip divider
                    i += 1

                    # Collect replace content until REPLACE marker
                    replace_lines: list[str] = []
                    while i < len(lines) and not updated_pattern.match(lines[i].strip()):
                        replace_lines.append(lines[i])
                        i += 1

                    if i >= len(lines):
                        break

                    # Found complete block - clean prompt artifacts
                    search_text, replace_text = clean_search_replace_block(
                        "".join(search_lines), "".join(replace_lines)
                    )
                    blocks.append((search_text, replace_text))

                    i += 1
                    break

                # Check if we hit closing fence without finding SEARCH
                if fence_pattern.match(lines[i].strip()):
                    break

                i += 1

        i += 1

    return blocks


def apply_diff_fenced_blocks(original: str, blocks: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Apply parsed diff-fenced blocks to original content.

    Returns (result, warnings) tuple. Skipped blocks are reported as warnings.
    Raises DiffFencedError only if no blocks provided.
    """
    if not blocks:
        raise DiffFencedError("No valid SEARCH/REPLACE blocks found")

    result = original
    warnings: list[str] = []

    for i, (search, replace) in enumerate(blocks, 1):
        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            warnings.append(f"Block {i}: SEARCH text not found")
        else:
            result = new_result

    return result, warnings


def format_failed_blocks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed blocks for the retry prompt."""
    parts: list[str] = []
    for block_num, search, replace in failed:
        parts.append(f"Block {block_num}:")
        parts.append(f"SEARCH:\n{search}")
        parts.append(f"REPLACE:\n{replace}")
        parts.append("")
    return "\n".join(parts)


class AiderDiffFencedAlgorithm(Algorithm):
    """Aider's diff-fenced format - filename inside code fence (for Gemini models)."""

    name = "aider_diff_fenced"
    description = "Aider diff-fenced format (filename inside fence)"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        llm_output, usage = await call_llm(model, user_prompt, system_prompt)

        blocks = parse_diff_fenced_blocks(llm_output)
        if not blocks:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No valid SEARCH/REPLACE blocks found",
                usage=usage,
            )

        # Apply blocks, collect failures
        result = initial
        failed_blocks: list[tuple[int, str, str]] = []

        for i, (search, replace) in enumerate(blocks, 1):
            new_result = replace_most_similar_chunk(result, search, replace)
            if new_result is None:
                failed_blocks.append((i, search, replace))
            else:
                result = new_result

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

        retry_blocks = parse_diff_fenced_blocks(retry_output)

        # Track which original blocks remain unrecovered
        warnings: list[str] = []

        if not retry_blocks:
            # Retry produced no blocks - all original failures become warnings
            for block_num, _search, _replace in failed_blocks:
                warnings.append(f"Block {block_num}: failed and retry produced no fix")
        else:
            # Apply retry blocks, track failures
            retry_failed_count = 0
            for _i, (search, replace) in enumerate(retry_blocks, 1):
                new_result = replace_most_similar_chunk(result, search, replace)
                if new_result is None:
                    retry_failed_count += 1
                else:
                    result = new_result

            # If retry returned fewer blocks than failures, or some retry blocks failed,
            # report the unrecovered count as warnings
            unrecovered = len(failed_blocks) - (len(retry_blocks) - retry_failed_count)
            if unrecovered > 0:
                warnings.append(
                    f"{unrecovered} block(s) unrecovered after retry "
                    f"(original failures: {[b[0] for b in failed_blocks]})"
                )

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

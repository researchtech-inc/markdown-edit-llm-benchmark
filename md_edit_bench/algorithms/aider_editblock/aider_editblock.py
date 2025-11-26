"""Aider's editblock algorithm with fuzzy matching."""

from __future__ import annotations

import re

from md_edit_bench.algorithms.aider_utils import clean_search_replace_block
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class AiderEditBlockError(Exception):
    """Raised when editblock parsing or application fails."""


def prep(content: str) -> tuple[str, list[str]]:
    """Normalize content and split into lines with newlines preserved."""
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines


def perfect_replace(
    whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
) -> str | None:
    """Try exact match replacement."""
    part_tup = tuple(part_lines)
    part_len = len(part_lines)

    for i in range(len(whole_lines) - part_len + 1):
        whole_tup = tuple(whole_lines[i : i + part_len])
        if part_tup == whole_tup:
            res = whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
            return "".join(res)
    return None


def match_but_for_leading_whitespace(whole_lines: list[str], part_lines: list[str]) -> str | None:
    """Check if lines match except for leading whitespace."""
    num = len(whole_lines)

    if not all(whole_lines[i].lstrip() == part_lines[i].lstrip() for i in range(num)):
        return None

    add = {
        whole_lines[i][: len(whole_lines[i]) - len(part_lines[i])]
        for i in range(num)
        if whole_lines[i].strip()
    }

    if len(add) != 1:
        return None

    return add.pop()


def replace_part_with_missing_leading_whitespace(
    whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
) -> str | None:
    """Handle case where LLM omitted some leading whitespace."""
    leading = [len(p) - len(p.lstrip()) for p in part_lines if p.strip()] + [
        len(p) - len(p.lstrip()) for p in replace_lines if p.strip()
    ]

    if leading and min(leading):
        num_leading = min(leading)
        part_lines = [p[num_leading:] if p.strip() else p for p in part_lines]
        replace_lines = [p[num_leading:] if p.strip() else p for p in replace_lines]

    num_part_lines = len(part_lines)

    for i in range(len(whole_lines) - num_part_lines + 1):
        add_leading = match_but_for_leading_whitespace(
            whole_lines[i : i + num_part_lines], part_lines
        )

        if add_leading is None:
            continue

        replace_lines = [add_leading + rline if rline.strip() else rline for rline in replace_lines]
        whole_lines = whole_lines[:i] + replace_lines + whole_lines[i + num_part_lines :]
        return "".join(whole_lines)

    return None


def perfect_or_whitespace(
    whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
) -> str | None:
    """Try perfect match first, then whitespace-flexible match."""
    res = perfect_replace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    return replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines)


def try_dotdotdots(whole: str, part: str, replace: str) -> str | None:
    """Handle edit blocks with ... elision markers."""
    dots_re = re.compile(r"(^\s*\.\.\.\n)", re.MULTILINE | re.DOTALL)

    part_pieces = re.split(dots_re, part)
    replace_pieces = re.split(dots_re, replace)

    if len(part_pieces) != len(replace_pieces):
        raise ValueError("Unpaired ... in SEARCH/REPLACE block")

    if len(part_pieces) == 1:
        return None

    all_dots_match = all(part_pieces[i] == replace_pieces[i] for i in range(1, len(part_pieces), 2))

    if not all_dots_match:
        raise ValueError("Unmatched ... in SEARCH/REPLACE block")

    part_pieces = [part_pieces[i] for i in range(0, len(part_pieces), 2)]
    replace_pieces = [replace_pieces[i] for i in range(0, len(replace_pieces), 2)]

    pairs = zip(part_pieces, replace_pieces, strict=True)
    for part_chunk, replace_chunk in pairs:
        if not part_chunk and not replace_chunk:
            continue

        if not part_chunk and replace_chunk:
            if not whole.endswith("\n"):
                whole += "\n"
            whole += replace_chunk
            continue

        if whole.count(part_chunk) == 0:
            raise ValueError("Dotdotdot chunk not found in document")
        if whole.count(part_chunk) > 1:
            raise ValueError("Dotdotdot chunk matches multiple locations")

        whole = whole.replace(part_chunk, replace_chunk, 1)

    return whole


def replace_most_similar_chunk(whole: str, part: str, replace: str) -> str | None:
    """Apply fuzzy matching to find and replace content."""
    whole, whole_lines = prep(whole)
    part, part_lines = prep(part)
    replace, replace_lines = prep(replace)

    res = perfect_or_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    if len(part_lines) > 2 and not part_lines[0].strip():
        skip_blank_line_part_lines = part_lines[1:]
        res = perfect_or_whitespace(whole_lines, skip_blank_line_part_lines, replace_lines)
        if res:
            return res

    try:
        res = try_dotdotdots(whole, part, replace)
        if res:
            return res
    except ValueError:
        pass

    return None


def parse_search_replace_blocks(content: str) -> list[tuple[str, str]]:
    """Parse SEARCH/REPLACE blocks from LLM output."""
    head_pattern = re.compile(r"^<{5,9} SEARCH>?\s*$")
    divider_pattern = re.compile(r"^={5,9}\s*$")
    updated_pattern = re.compile(r"^>{5,9} REPLACE\s*$")

    lines = content.splitlines(keepends=True)
    blocks: list[tuple[str, str]] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if head_pattern.match(line.strip()):
            search_text: list[str] = []
            i += 1
            while i < len(lines) and not divider_pattern.match(lines[i].strip()):
                search_text.append(lines[i])
                i += 1

            if i >= len(lines) or not divider_pattern.match(lines[i].strip()):
                raise AiderEditBlockError("Expected '=======' after SEARCH block")

            replace_text: list[str] = []
            i += 1
            while i < len(lines) and not updated_pattern.match(lines[i].strip()):
                replace_text.append(lines[i])
                i += 1

            if i >= len(lines) or not updated_pattern.match(lines[i].strip()):
                raise AiderEditBlockError("Expected '>>>>>>> REPLACE' after replace content")

            # Clean prompt artifacts from parsed blocks
            search_clean, replace_clean = clean_search_replace_block(
                "".join(search_text), "".join(replace_text)
            )
            blocks.append((search_clean, replace_clean))

        i += 1

    if not blocks:
        raise AiderEditBlockError("No valid SEARCH/REPLACE blocks found")

    return blocks


def format_failed_blocks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed blocks for the retry prompt."""
    parts: list[str] = []
    for block_num, search, replace in failed:
        parts.append(f"Block {block_num}:")
        parts.append(f"SEARCH:\n{search}")
        parts.append(f"REPLACE:\n{replace}")
        parts.append("")
    return "\n".join(parts)


def apply_editblocks(
    original: str, blocks_text: str
) -> tuple[str, list[str], list[tuple[int, str, str]]]:
    """Parse and apply editblocks to original content.

    Returns (result, warnings, failed_blocks) tuple.
    failed_blocks contains tuples of (block_num, search, replace) for blocks that couldn't be applied.
    Raises AiderEditBlockError only for parse errors (no blocks, missing markers).
    """
    blocks = parse_search_replace_blocks(blocks_text)

    result = original
    warnings: list[str] = []
    failed_blocks: list[tuple[int, str, str]] = []

    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            if not result.endswith("\n"):
                result += "\n"
            result += replace
            continue

        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            failed_blocks.append((i, search, replace))
            warnings.append(f"Block {i}: could not find match for SEARCH text")
        else:
            result = new_result

    return result, warnings, failed_blocks


class AiderEditBlockAlgorithm(Algorithm):
    """Aider's editblock format with fuzzy matching for better robustness."""

    name = "aider_editblock"
    description = "Aider's SEARCH/REPLACE blocks with fuzzy matching"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        blocks_text, usage = await call_llm(model, user_prompt, system_prompt)

        try:
            result, warnings, failed_blocks = apply_editblocks(initial, blocks_text)
        except AiderEditBlockError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

        # If no failures, return immediately
        if not failed_blocks:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Pass 2: Retry failed blocks with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_blocks=format_failed_blocks(failed_blocks),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        # Parse retry blocks
        try:
            retry_blocks = parse_search_replace_blocks(retry_output)
        except AiderEditBlockError:
            # Retry produced no valid blocks - all original failures remain as warnings
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Apply retry blocks
        retry_failed_count = 0
        for _i, (search, replace) in enumerate(retry_blocks, 1):
            if not search.strip():
                if not result.endswith("\n"):
                    result += "\n"
                result += replace
                continue

            new_result = replace_most_similar_chunk(result, search, replace)
            if new_result is None:
                retry_failed_count += 1
            else:
                result = new_result

        # Update warnings based on retry results
        unrecovered = len(failed_blocks) - (len(retry_blocks) - retry_failed_count)
        if unrecovered > 0:
            warnings = [
                f"{unrecovered} block(s) unrecovered after retry "
                f"(original failures: {[b[0] for b in failed_blocks]})"
            ]
        else:
            warnings = []

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

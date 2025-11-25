"""Aider's editblock algorithm with fuzzy matching."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import clean_search_replace_block
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """You are an expert document editor. Given a document and requested changes, generate SEARCH/REPLACE blocks to implement the changes.

## SEARCH/REPLACE Format

Use this format for each change:

<<<<<<< SEARCH
exact text to find
=======
replacement text
>>>>>>> REPLACE

## CRITICAL RULES

1. **SEARCH text must match closely**: Copy text from the original document as accurately as possible. The system uses fuzzy matching and can handle minor whitespace differences.

2. **One block per change**: Use separate SEARCH/REPLACE blocks for changes in different parts of the document.

3. **Include context**: The SEARCH text should include 1-2 lines before and after the text being changed to ensure unique matching.

4. **For additions**: Include the line(s) before where you want to add content in SEARCH, then include those same lines PLUS the new content in REPLACE.

5. **For deletions**: Include the text to delete in SEARCH, and omit it from REPLACE (keeping surrounding context).

## Example

To add a paragraph after "## Introduction":

<<<<<<< SEARCH
## Introduction

This is the first paragraph.
=======
## Introduction

This is the first paragraph.

This is a new paragraph being added.
>>>>>>> REPLACE

Output ONLY the search/replace blocks, no explanations."""

USER_PROMPT = """Generate SEARCH/REPLACE blocks to implement the following changes.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>

Generate the search/replace blocks. Remember:
- SEARCH text should closely match text in the original
- Include enough context to uniquely identify each location
- Use separate blocks for separate changes

Output the search/replace blocks:"""


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


def apply_editblocks(original: str, blocks_text: str) -> str:
    """Parse and apply editblocks to original content."""
    blocks = parse_search_replace_blocks(blocks_text)

    result = original
    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            if not result.endswith("\n"):
                result += "\n"
            result += replace
            continue

        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            raise AiderEditBlockError(
                f"Block {i}: Could not find a suitable match for SEARCH text in document"
            )
        result = new_result

    return result


@register_algorithm
class AiderEditBlockAlgorithm(Algorithm):
    """Aider's editblock format with fuzzy matching for better robustness."""

    name = "aider_editblock"
    description = "Aider's SEARCH/REPLACE blocks with fuzzy matching"
    accepts_model = True
    default_model = "openai/gpt-oss-120b"

    async def apply(
        self,
        initial: str,
        changes: str,
        model: str | None = None,
    ) -> AlgorithmResult:
        model = model or self.default_model
        assert model is not None

        user_prompt = USER_PROMPT.format(initial=initial, changes=changes)

        blocks_text, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        try:
            result = apply_editblocks(initial, blocks_text)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )
        except AiderEditBlockError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

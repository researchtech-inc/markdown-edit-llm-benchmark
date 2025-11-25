"""Aider's fuzzy matching utilities for search/replace operations.

Ported from aider/coders/editblock_coder.py to provide robust matching that handles:
- Exact matches
- Whitespace/indentation differences
- Ellipsis (...) in search blocks

These utilities power Aider's high success rate with LLM-generated search/replace blocks.
"""

from __future__ import annotations

import re


def prep(content: str) -> tuple[str, list[str]]:
    """Prepare content for matching by normalizing newlines and splitting to lines.

    Args:
        content: Raw text content

    Returns:
        Tuple of (normalized_content, lines_with_endings)
    """
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines


def perfect_replace(
    whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
) -> str | None:
    """Perform exact tuple-based matching and replacement.

    Args:
        whole_lines: All lines in the document
        part_lines: Lines to search for
        replace_lines: Lines to replace with

    Returns:
        Modified content if exact match found, None otherwise
    """
    part_tup = tuple(part_lines)
    part_len = len(part_lines)

    for i in range(len(whole_lines) - part_len + 1):
        whole_tup = tuple(whole_lines[i : i + part_len])
        if part_tup == whole_tup:
            res = whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
            return "".join(res)

    return None


def match_but_for_leading_whitespace(whole_lines: list[str], part_lines: list[str]) -> str | None:
    """Check if lines match except for leading whitespace, return the common prefix.

    Args:
        whole_lines: Lines from document to check
        part_lines: Lines to match against

    Returns:
        Common leading whitespace prefix if all lines match (except for that prefix), None otherwise
    """
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
    """Handle cases where LLM omits or includes partial leading whitespace.

    LLMs often mess up leading whitespace uniformly across SEARCH and REPLACE blocks.
    This function outdents everything by the maximum possible amount, then looks for
    matches ignoring leading whitespace differences.

    Args:
        whole_lines: All lines in document
        part_lines: Lines to search for (may have incorrect indentation)
        replace_lines: Lines to replace with (may have incorrect indentation)

    Returns:
        Modified content if match found, None otherwise
    """
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
    """Try perfect match first, then flexible whitespace matching.

    Args:
        whole_lines: All lines in document
        part_lines: Lines to search for
        replace_lines: Lines to replace with

    Returns:
        Modified content if any match found, None otherwise
    """
    res = perfect_replace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    return replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines)


def try_dotdotdots(whole: str, part: str, replace: str) -> str | None:
    """Handle search/replace blocks that use ... as ellipsis markers.

    LLMs sometimes use ... to indicate "code continues here unchanged".
    This function:
    1. Returns None if no ... found
    2. Raises ValueError if ... usage is malformed/ambiguous
    3. Returns modified content if ... blocks match perfectly

    Args:
        whole: Full document content
        part: Search text (may contain ... markers)
        replace: Replacement text (may contain ... markers)

    Returns:
        Modified content if successful, None if no ellipsis found

    Raises:
        ValueError: If ellipsis usage is malformed or creates ambiguity
    """
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

        if whole.count(part_chunk) != 1:
            raise ValueError("Ellipsis block ambiguous or not found")

        whole = whole.replace(part_chunk, replace_chunk, 1)

    return whole


def try_substring_match(whole: str, part: str, replace: str) -> str | None:
    """Handle cases where search text is a substring within larger lines.

    LLMs sometimes provide only part of a long line as context (e.g., just the
    second sentence). This function finds unique substring matches and performs
    the replacement.

    Args:
        whole: Full document content
        part: Text to search for (may be substring of actual lines)
        replace: Text to replace with

    Returns:
        Modified content if unique substring match found, None otherwise
    """
    part_stripped = part.strip()

    # Skip if search text is too short (likely to match multiple places)
    if len(part_stripped) < 20:
        return None

    # Skip if search text spans multiple paragraphs (use line-based matching instead)
    if "\n\n" in part_stripped:
        return None

    # Count occurrences
    count = whole.count(part_stripped)

    if count == 1:
        return whole.replace(part_stripped, replace.strip(), 1)

    return None


def replace_most_similar_chunk(whole: str, part: str, replace: str) -> str | None:
    """Main entry point for search/replace with fallback strategies.

    Tries multiple strategies in order of increasing flexibility:
    1. Perfect exact match
    2. Perfect match with flexible leading whitespace
    3. Skip spurious leading blank line
    4. Handle ellipsis (...) markers
    5. Substring matching (for partial line matches)

    Args:
        whole: Full document content
        part: Text to search for
        replace: Text to replace with

    Returns:
        Modified content if any strategy succeeds, None if all fail
    """
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

    # Try substring matching for cases where LLM provides partial lines
    res = try_substring_match(whole, part, replace)
    if res:
        return res

    return None


DEFAULT_FENCE = ("```", "```")

# Common prompt artifacts that LLMs incorrectly include in their output
PROMPT_ARTIFACTS = [
    "</original_document>",
    "<original_document>",
    "</requested_changes>",
    "<requested_changes>",
    "</original>",
    "<original>",
    "</changes>",
    "<changes>",
]


def clean_llm_output(text: str) -> str:
    """Remove common prompt artifacts from LLM output.

    LLMs sometimes include closing XML tags or other prompt delimiters in their
    output. This function strips those artifacts to prevent matching failures.

    Args:
        text: Raw LLM output

    Returns:
        Cleaned text with prompt artifacts removed
    """
    for artifact in PROMPT_ARTIFACTS:
        text = text.replace(artifact, "")
    return text


def clean_search_replace_block(search: str, replace: str) -> tuple[str, str]:
    """Clean prompt artifacts from a search/replace block pair.

    Args:
        search: Search text from LLM
        replace: Replace text from LLM

    Returns:
        Tuple of (cleaned_search, cleaned_replace)
    """
    return clean_llm_output(search), clean_llm_output(replace)


def strip_quoted_wrapping(
    res: str, fname: str | None = None, fence: tuple[str, str] = DEFAULT_FENCE
) -> str:
    """Remove fence markers and optional filename from LLM output.

    LLMs sometimes wrap content in markdown fences:
        filename.ext
        ```
        actual content
        ```

    This function strips those wrapping elements.

    Args:
        res: Raw LLM output
        fname: Optional filename to check for and remove
        fence: Tuple of (opening_fence, closing_fence)

    Returns:
        Cleaned content with trailing newline
    """
    if not res:
        return res

    lines = res.splitlines()

    if fname and lines and lines[0].strip().endswith(fname):
        lines = lines[1:]

    if lines and lines[0].startswith(fence[0]) and lines[-1].startswith(fence[1]):
        lines = lines[1:-1]

    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"

    return result

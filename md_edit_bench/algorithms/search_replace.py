"""Search/replace algorithm - LLM outputs search/replace blocks (Aider-style)."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """## Search/Replace Format

Use this format for each change:

<<<<<<< SEARCH
exact text to find
=======
replacement text
>>>>>>> REPLACE

You can use 5-9 angle brackets, equals signs, or greater-than signs. All formats below are valid:
- `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE` (7 chars)
- `<<<<<< SEARCH` / `======` / `>>>>>> REPLACE` (6 chars)
- etc.

## CRITICAL RULES

1. **SEARCH text must be EXACT**: Copy the exact text from the original document, character for character, including all whitespace and indentation. Include enough context (a few lines) to uniquely identify the location.

2. **One block per change**: Use separate SEARCH/REPLACE blocks for changes in different parts of the document.

3. **Include context**: The SEARCH text should include 1-2 lines before and after the text being changed to ensure unique matching.

4. **For additions**: Include the line(s) before where you want to add content in SEARCH, then include those same lines PLUS the new content in REPLACE.

5. **For deletions**: Include the text to delete in SEARCH, and omit it from REPLACE (keeping surrounding context).

6. **IMPORTANT - Make each block complete and independent**: When making multiple related changes in the same area, include ALL the affected text in a SINGLE block. Do NOT split related changes into multiple blocks that depend on each other. Each SEARCH block must match text from the ORIGINAL document, not from an intermediate state.

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

## BAD Example (DON'T DO THIS)

Don't split related changes like this:

<<<<<<< SEARCH
## Introduction
=======
## Introduction

New subtitle added here
>>>>>>> REPLACE

<<<<<<< SEARCH
## Introduction

New subtitle added here

Paragraph text
=======
## Introduction

New subtitle added here

Modified paragraph text
>>>>>>> REPLACE

Instead, make ONE complete block:

<<<<<<< SEARCH
## Introduction

Paragraph text
=======
## Introduction

New subtitle added here

Modified paragraph text
>>>>>>> REPLACE"""

SYSTEM_PROMPT = f"""You are an expert document editor. Given a document and requested changes, generate search/replace blocks to implement the changes.

{FORMAT_SPECIFICATION}

Output ONLY the search/replace blocks, no explanations."""

USER_PROMPT = f"""Generate search/replace blocks to implement the following changes.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}

Output the search/replace blocks:"""


class SearchReplaceError(Exception):
    """Raised when a search/replace block cannot be applied safely."""


def normalize_paragraph_structure(search: str, replace: str) -> str:
    """Normalize paragraph structure in replace to match search.

    LLMs sometimes split single paragraphs in SEARCH into multiple paragraphs in REPLACE.
    This function detects such cases and merges the paragraphs to preserve formatting.

    Rules:
    - If search has consecutive non-blank lines (single paragraph)
    - And replace has blank lines splitting similar content
    - Then merge replace paragraphs to match search structure
    """
    replace_lines: list[str] = replace.split("\n")

    # Count paragraph breaks in search and replace (excluding structural breaks after headers/lists)
    def count_prose_paragraph_breaks(text: str) -> int:
        """Count paragraph breaks that are within prose, not structural."""
        lines = text.split("\n")
        count = 0
        i = 0
        while i < len(lines) - 1:
            if not lines[i].strip():
                # This is a blank line - is the next non-blank line a header/list?
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                if next_idx < len(lines):
                    next_line = lines[next_idx].strip()
                    # Skip if it's a structural element
                    if not (
                        next_line.startswith("#")
                        or next_line.startswith("-")
                        or next_line.startswith("*")
                    ):
                        # Also check previous line - if it's a header, this is structural
                        prev_idx = i - 1
                        while prev_idx >= 0 and not lines[prev_idx].strip():
                            prev_idx -= 1
                        if prev_idx >= 0:
                            prev_line = lines[prev_idx].strip()
                            if not (
                                prev_line.startswith("#")
                                or prev_line.startswith("-")
                                or prev_line.startswith("*")
                            ):
                                count += 1
            i += 1
        return count

    search_prose_breaks = count_prose_paragraph_breaks(search)
    replace_prose_breaks = count_prose_paragraph_breaks(replace)

    # If search has fewer prose paragraph breaks than replace, check if we should normalize
    # Strategy: if REPLACE is splitting existing content from SEARCH, normalize
    # If REPLACE is adding significant new content as new paragraphs, don't normalize
    if search_prose_breaks < replace_prose_breaks:
        # Get the paragraphs from replace (split by double newline)
        replace_paragraphs = [p.strip() for p in replace.split("\n\n") if p.strip()]
        # Filter out headers/lists to get prose paragraphs
        replace_prose_paras = [
            p
            for p in replace_paragraphs
            if not p.startswith("#") and not p.startswith("-") and not p.startswith("*")
        ]

        # If we have multiple prose paragraphs in replace, check if they're splitting SEARCH content
        # or adding new content.
        #
        # Key insight: if SEARCH has multiple sentences in a single paragraph (e.g., "Sentence 1. Sentence 2.")
        # and REPLACE splits them into multiple paragraphs, we should normalize.
        # But if REPLACE keeps those sentences together and ADDS new paragraphs, don't normalize.
        #
        # Heuristic: Extract the prose content from SEARCH (single paragraph).
        # Check if words from SEARCH appear in multiple REPLACE paragraphs.
        # If the second paragraph of REPLACE contains significant words from SEARCH, it's a split.
        should_normalize = True
        if len(replace_prose_paras) >= 2:
            # Get prose from search (excluding headers/lists) - should be a single paragraph
            search_prose_lines = [
                line
                for line in search.split("\n")
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith("-")
                and not line.strip().startswith("*")
            ]
            search_prose = " ".join(search_prose_lines)

            # Extract significant words from SEARCH (words longer than 5 chars, case-insensitive)
            search_words = {
                word.lower() for word in search_prose.split() if len(word.strip(".,!?")) > 5
            }

            # Check how many search words appear in the second paragraph of REPLACE
            second_para = replace_prose_paras[1].lower()
            matching_words = sum(1 for word in search_words if word in second_para)

            # If less than 20% of search words appear in the second paragraph, it's likely new content
            if search_words and matching_words / len(search_words) < 0.2:
                should_normalize = False

        if not should_normalize:
            return replace
        # Strategy: replace blank lines with single spaces to merge paragraphs
        # But preserve section headers (lines starting with #) and list items

        result_lines: list[str] = []
        i = 0
        while i < len(replace_lines):
            line = replace_lines[i]

            # Keep headers, blank lines before headers, and list items as-is
            if (
                line.strip().startswith("#")
                or line.strip().startswith("-")
                or line.strip().startswith("*")
            ):
                result_lines.append(line)
                i += 1
                continue

            # If we hit a blank line
            if not line.strip():
                # Check previous line - if it's a header/list, this blank is structural
                if result_lines:
                    prev_line = result_lines[-1].strip()
                    if (
                        prev_line.startswith("#")
                        or prev_line.startswith("-")
                        or prev_line.startswith("*")
                    ):
                        result_lines.append(line)
                        i += 1
                        continue

                # Look ahead - if next non-blank line is a header/list, keep the blank
                next_idx = i + 1
                while next_idx < len(replace_lines) and not replace_lines[next_idx].strip():
                    next_idx += 1

                if next_idx < len(replace_lines):
                    next_line = replace_lines[next_idx].strip()
                    if (
                        next_line.startswith("#")
                        or next_line.startswith("-")
                        or next_line.startswith("*")
                    ):
                        result_lines.append(line)
                        i += 1
                        continue

                # Otherwise, this is a paragraph break within prose - skip it
                # and merge the next line onto the current line
                i += 1
                if (
                    i < len(replace_lines)
                    and replace_lines[i].strip()
                    and result_lines
                    and result_lines[-1].strip()
                ):
                    result_lines[-1] = result_lines[-1].rstrip() + " " + replace_lines[i].lstrip()
                    i += 1
                continue

            result_lines.append(line)
            i += 1

        return "\n".join(result_lines)

    return replace


def parse_blocks(blocks_text: str) -> list[tuple[str, str]]:
    """Parse search/replace blocks from LLM output."""
    pattern = r"<{5,9} SEARCH\n(.*?)\n={5,9}\n(.*?)\n>{5,9} REPLACE"
    blocks: list[tuple[str, str]] = re.findall(pattern, blocks_text, re.DOTALL)

    if not blocks:
        pattern = r"<{5,9}\n(.*?)\n={5,9}\n(.*?)\n>{5,9}"
        blocks = re.findall(pattern, blocks_text, re.DOTALL)

    # Clean prompt artifacts and normalize paragraph structure
    cleaned_blocks: list[tuple[str, str]] = []
    for search, replace in blocks:
        search_clean, replace_clean = clean_search_replace_block(search, replace)
        replace_normalized = normalize_paragraph_structure(search_clean, replace_clean)
        cleaned_blocks.append((search_clean, replace_normalized))

    return cleaned_blocks


def apply_search_replace(original: str, blocks_text: str) -> tuple[str, list[str]]:
    """Parse and apply search/replace blocks using fuzzy matching on evolving document.

    Uses replace_most_similar_chunk for robust matching that handles:
    - Exact matches (preferred)
    - Whitespace differences
    - Minor text variations (80% similarity threshold)

    Applies blocks sequentially to evolving document state, allowing later blocks
    to reference text created by earlier blocks.

    Returns (result, warnings) tuple. Skipped blocks are reported as warnings.
    Raises SearchReplaceError only for unrecoverable errors (no blocks, empty search).
    """
    blocks = parse_blocks(blocks_text)

    if not blocks:
        raise SearchReplaceError("No valid search/replace blocks found")

    result = original
    warnings: list[str] = []
    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            raise SearchReplaceError(f"Block {i}: empty search text")

        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            warnings.append(f"Block {i}: could not find match for search text")
        else:
            result = new_result

    return result, warnings


@register_algorithm
class SearchReplaceAlgorithm(Algorithm):
    """LLM outputs search/replace blocks (Aider-style), then parsed and applied."""

    name = "search_replace"
    description = "LLM outputs search/replace blocks, then parsed and applied"
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
            result, warnings = apply_search_replace(initial, blocks_text)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )
        except SearchReplaceError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

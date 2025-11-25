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

SYSTEM_PROMPT = """You are an expert document editor. Given a document and requested changes, generate search/replace blocks to implement the changes.

## Search/Replace Format

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

USER_PROMPT = """Generate search/replace blocks to implement the following changes.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>

Generate the search/replace blocks. Remember:
- SEARCH text must EXACTLY match text in the original (copy-paste)
- Include enough context to uniquely identify each location
- Use separate blocks for separate changes

Output the search/replace blocks:"""


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


def apply_search_replace(original: str, blocks_text: str) -> str:
    """Parse and apply search/replace blocks using fuzzy matching on evolving document.

    Uses replace_most_similar_chunk for robust matching that handles:
    - Exact matches (preferred)
    - Whitespace differences
    - Minor text variations (80% similarity threshold)

    Applies blocks sequentially to evolving document state, allowing later blocks
    to reference text created by earlier blocks.
    """
    blocks = parse_blocks(blocks_text)

    if not blocks:
        raise SearchReplaceError("No valid search/replace blocks found")

    result = original
    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            raise SearchReplaceError(f"Block {i}: empty search text")

        new_result = replace_most_similar_chunk(result, search, replace)
        if new_result is None:
            raise SearchReplaceError(f"Block {i}: could not find match for search text")
        result = new_result

    return result


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
            result = apply_search_replace(initial, blocks_text)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )
        except SearchReplaceError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

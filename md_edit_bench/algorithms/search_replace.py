"""Search/replace algorithm - LLM outputs search/replace blocks (Aider-style)."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
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

## CRITICAL RULES

1. **SEARCH text must be EXACT**: Copy the exact text from the original document, character for character. Include enough context (a few lines) to uniquely identify the location.

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

## ORIGINAL DOCUMENT
```
{initial}
```

## REQUESTED CHANGES
{changes}

Generate the search/replace blocks. Remember:
- SEARCH text must EXACTLY match text in the original (copy-paste)
- Include enough context to uniquely identify each location
- Use separate blocks for separate changes

Output the search/replace blocks:"""


class SearchReplaceError(Exception):
    """Raised when a search/replace block cannot be applied safely."""


def apply_search_replace(original: str, blocks_text: str) -> str:
    """Parse and apply search/replace blocks to original content.

    Raises SearchReplaceError if any block cannot be matched unambiguously.
    All blocks are validated against the original document first, then applied sequentially.
    """
    pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
    blocks: list[tuple[str, str]] = re.findall(pattern, blocks_text, re.DOTALL)

    if not blocks:
        pattern = r"<<<<<<\n(.*?)\n======\n(.*?)\n>>>>>>"
        blocks = re.findall(pattern, blocks_text, re.DOTALL)

    if not blocks:
        raise SearchReplaceError("No valid search/replace blocks found")

    # Validate all blocks against original first to catch overlapping/conflicting blocks
    normalized_blocks: list[tuple[str, str, bool]] = []  # (search, replace, is_normalized)
    for i, (search, replace) in enumerate(blocks, 1):
        count = original.count(search)
        if count == 1:
            normalized_blocks.append((search, replace, False))
            continue
        if count > 1:
            raise SearchReplaceError(
                f"Block {i}: search text matches {count} locations (ambiguous)"
            )

        search_normalized = search.strip()
        if not search_normalized:
            raise SearchReplaceError(f"Block {i}: empty search text")

        count = original.count(search_normalized)
        if count == 1:
            normalized_blocks.append((search_normalized, replace.strip(), True))
            continue
        if count > 1:
            raise SearchReplaceError(
                f"Block {i}: normalized search matches {count} locations (ambiguous)"
            )

        raise SearchReplaceError(f"Block {i}: search text not found in original document")

    # Apply all validated blocks
    result = original
    for search, replace, _ in normalized_blocks:
        result = result.replace(search, replace, 1)

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

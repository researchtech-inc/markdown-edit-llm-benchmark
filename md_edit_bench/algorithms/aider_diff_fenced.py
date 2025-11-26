"""Aider diff-fenced algorithm - filename INSIDE code fence for Gemini models."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """# *SEARCH/REPLACE block* Format Rules:

Every *SEARCH/REPLACE block* must use this format:
1. The opening fence with language: ```markdown
2. The document name on the next line: document.md
3. The start of search block: <<<<<<< SEARCH
4. A contiguous chunk of lines to search for in the existing document
5. The dividing line: =======
6. The lines to replace into the document
7. The end of the replace block: >>>>>>> REPLACE
8. The closing fence: ```

# Critical Requirements:

- Every *SEARCH* section must *EXACTLY MATCH* existing document content, character for character
- SEARCH text is matched line-by-line. Always include COMPLETE lines - never start or end SEARCH mid-line
- Include enough lines to uniquely match each location (2-3 lines of context)
- Keep blocks concise - only include changing lines plus minimal context
- Multiple blocks can be used for multiple changes
- For additions: include surrounding lines in SEARCH, add new content in REPLACE
- For deletions: include text to delete in SEARCH, omit it from REPLACE

# Example:

```markdown
document.md
<<<<<<< SEARCH
## Introduction

This is the first paragraph.
=======
## Introduction

This is the first paragraph.

This is a new paragraph being added.
>>>>>>> REPLACE
```"""

SYSTEM_PROMPT = f"""Act as an expert document editor.
You will receive a markdown document and a request for changes.
Output the changes using *SEARCH/REPLACE blocks* in the diff-fenced format.

{FORMAT_SPECIFICATION}

ONLY output SEARCH/REPLACE blocks, no explanations."""

USER_PROMPT = f"""Edit the following document according to the requested changes.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}

Output the *SEARCH/REPLACE blocks* in diff-fenced format:"""


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


@register_algorithm
class AiderDiffFencedAlgorithm(Algorithm):
    """Aider's diff-fenced format - filename inside code fence (for Gemini models)."""

    name = "aider_diff_fenced"
    description = "Aider diff-fenced format (filename inside fence)"
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
        llm_output, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        try:
            blocks = parse_diff_fenced_blocks(llm_output)
            result, warnings = apply_diff_fenced_blocks(initial, blocks)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )
        except DiffFencedError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

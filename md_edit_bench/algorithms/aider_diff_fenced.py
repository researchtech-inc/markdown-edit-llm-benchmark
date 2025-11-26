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
- SEARCH text is matched line-by-line. Always include COMPLETE lines from beginning to end - NEVER extract partial sentences or split lines
- If a line has multiple sentences, include THE ENTIRE LINE in SEARCH, not just one sentence
- Include enough lines to uniquely match each location (typically 2-4 lines including the lines being changed)
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


def normalize_line_structure(search: str, replace: str) -> str:
    """Normalize REPLACE block to match line structure of SEARCH block.

    LLMs often split multi-sentence lines in REPLACE when they should stay together.
    This function joins them back based on SEARCH structure.
    """
    # Remove trailing whitespace but preserve leading whitespace
    search_lines: list[str] = search.rstrip().split("\n")
    replace_lines: list[str] = replace.rstrip().split("\n")

    # Find lines in SEARCH that have multiple sentences
    # (period/question/exclamation followed by space and capital letter)
    search_multi_sentence: dict[int, int] = {}
    for i, line in enumerate(search_lines):
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith("-")
            and not stripped.startswith("*")
            and re.search(r"[.!?]\s+[A-Z]", line)
        ):
            # Count approximate number of sentences
            num_sentences = len(re.findall(r"[.!?](?:\s|$)", line))
            search_multi_sentence[i] = num_sentences

    # If no multi-sentence lines, return as-is
    if not search_multi_sentence:
        return replace

    # Align and restructure
    result: list[str] = []
    r_idx = 0
    for s_idx, search_line in enumerate(search_lines):
        if r_idx >= len(replace_lines):
            break

        # Empty line - copy from REPLACE
        if not search_line.strip():
            # Skip any empty lines in replace
            while r_idx < len(replace_lines) and not replace_lines[r_idx].strip():
                r_idx += 1
            result.append("")
            continue

        # Headers - copy from REPLACE
        if search_line.strip().startswith("#"):
            if r_idx < len(replace_lines):
                result.append(replace_lines[r_idx])
                r_idx += 1
            continue

        # Multi-sentence line - collect and join sentences from REPLACE
        if s_idx in search_multi_sentence:
            num_sentences = search_multi_sentence[s_idx]
            collected_parts: list[str] = []
            collected_count = 0

            while r_idx < len(replace_lines) and collected_count < num_sentences:
                r_line = replace_lines[r_idx]

                # Skip blank lines
                if not r_line.strip():
                    r_idx += 1
                    continue

                # Stop if we hit a new header or bullet point
                if r_line.strip().startswith("#") or r_line.strip().startswith("-"):
                    break

                # Stop if we hit bold text that looks like a new section
                # (but allow it if we haven't collected anything yet - might be the content itself)
                if (
                    collected_parts
                    and r_line.strip().startswith("**")
                    and r_line.strip().endswith("**:")
                ):
                    break

                # Collect this line
                collected_parts.append(r_line.strip())
                collected_count += len(re.findall(r"[.!?](?:\s|$)", r_line))
                r_idx += 1

            # Join collected parts
            if collected_parts:
                indent = len(search_line) - len(search_line.lstrip())
                result.append(" " * indent + " ".join(collected_parts))
        # Regular line - copy from REPLACE
        elif r_idx < len(replace_lines):
            result.append(replace_lines[r_idx])
            r_idx += 1

    # Append any remaining REPLACE lines
    while r_idx < len(replace_lines):
        result.append(replace_lines[r_idx])
        r_idx += 1

    return "\n".join(result)


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

                    # Normalize line structure to match SEARCH
                    replace_text = normalize_line_structure(search_text, replace_text)

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

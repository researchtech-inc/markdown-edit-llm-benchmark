"""Git diff algorithm - LLM generates unified diff format."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """## Unified Diff Format

The diff format uses:
- `---` and `+++` lines to indicate the original and modified file
- `@@ -start,count +start,count @@` hunk headers (line numbers are hints, context lines matter more)
- Lines starting with `-` are removed from original
- Lines starting with `+` are added in the new version
- Lines starting with ` ` (space) are context (unchanged)

## CRITICAL: Replacing vs Adding Content

When you need to MODIFY existing text, you MUST remove the old line and add the new line:

WRONG - treats old as context, creates duplicate:
```diff
 Old text here
+New text here
```

CORRECT - removes old, adds new:
```diff
-Old text here
+New text here
```

## CRITICAL RULES

1. **Use exact line content**: The `-` lines and context lines MUST match the EXACT text from the original document. Copy-paste, do not paraphrase.

2. **Include context**: Each hunk should include 2-3 lines of unchanged context before and after to locate changes.

3. **Preserve formatting**: Keep the exact whitespace, indentation, and line breaks from the original.

4. **Small focused hunks**: Make multiple small hunks rather than one large hunk when changes are in different parts.

5. **Preserve line structure**: If multiple sentences are on one line in the original, keep them on one line.

## Output Format
Output ONLY the unified diff. No explanations, no markdown code blocks around it. Just the raw diff starting with `--- a/` line."""

SYSTEM_PROMPT = f"""You are an expert at generating unified diff patches to edit markdown documents.

## Your Task
Generate a unified diff (git diff format) that implements the requested changes to the document.

{FORMAT_SPECIFICATION}"""

USER_PROMPT = f"""Generate a unified diff to implement the following changes to the document.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}

Output ONLY the diff:"""


class DiffError(Exception):
    """Raised when a diff cannot be applied."""


def _normalize_blank_lines(text: str) -> str:
    """Normalize consecutive blank lines to single blank lines.

    This helps match diffs where LLMs incorrectly assume extra blank lines exist.
    """
    return re.sub(r"\n\n\n+", "\n\n", text)


def _apply_hunk_with_fallbacks(document: str, before_text: str, after_text: str) -> str | None:
    """Try multiple strategies to apply a hunk to the document."""
    # Strategy 1: Direct fuzzy match
    result = replace_most_similar_chunk(document, before_text, after_text)
    if result is not None:
        return result

    # Strategy 2: Normalize blank lines
    doc_normalized = _normalize_blank_lines(document)
    before_normalized = _normalize_blank_lines(before_text)
    after_normalized = _normalize_blank_lines(after_text)

    if doc_normalized != document or before_normalized != before_text:
        result = replace_most_similar_chunk(doc_normalized, before_normalized, after_normalized)
        if result is not None:
            return result

    # Strategy 3: Try without leading blank lines
    if before_text.startswith("\n"):
        before_no_leading = before_text.lstrip("\n")
        after_no_leading = after_text.lstrip("\n")
        if before_no_leading:
            result = replace_most_similar_chunk(document, before_no_leading, after_no_leading)
            if result is not None:
                return result

    # Strategy 4: Fuzzy line matching for lines modified by previous hunks
    before_lines_list = before_text.split("\n")
    if len(before_lines_list) >= 2:
        pattern_before = before_text
        pattern_after = after_text
        changed = False

        for before_line in before_lines_list:
            if before_line and len(before_line) > 10 and not before_line.strip().startswith("#"):
                doc_lines = document.split("\n")
                for doc_line in doc_lines:
                    if doc_line.startswith(before_line) and len(doc_line) > len(before_line):
                        pattern_before = pattern_before.replace(before_line, doc_line, 1)
                        pattern_after = pattern_after.replace(before_line, doc_line, 1)
                        changed = True
                        break

        if changed:
            result = replace_most_similar_chunk(document, pattern_before, pattern_after)
            if result is not None:
                return result

    return None


def hunk_to_before_after(hunk_lines: list[tuple[str, str]]) -> tuple[str, str]:
    """Convert hunk lines to before/after text for fuzzy matching."""
    before_lines: list[str] = []
    after_lines: list[str] = []

    for op, content in hunk_lines:
        if op == " ":  # Context line - appears in both
            before_lines.append(content)
            after_lines.append(content)
        elif op == "-":  # Deletion - only in before
            before_lines.append(content)
        elif op == "+":  # Addition - only in after
            after_lines.append(content)

    # Fix malformed diffs that have duplicate context lines at the end
    # LLMs sometimes repeat the last context line incorrectly
    if len(before_lines) >= 2 and before_lines[-1] == before_lines[-2]:
        before_lines = before_lines[:-1]
    if len(after_lines) >= 2 and after_lines[-1] == after_lines[-2]:
        after_lines = after_lines[:-1]

    # Clean prompt artifacts from the result
    return clean_search_replace_block("\n".join(before_lines), "\n".join(after_lines))


def parse_and_apply_diff(original: str, diff_text: str) -> tuple[str, list[str]]:
    """Parse unified diff and apply using context-based fuzzy matching.

    Ignores line numbers from @@ headers - uses context lines to locate changes.
    Applies hunks sequentially to evolving document state.

    Returns (result, warnings) tuple. Skipped hunks are reported as warnings.
    Raises DiffError only if no hunks found.
    """
    # Clean up diff text - remove markdown code blocks if present
    diff_clean = diff_text.strip()
    if diff_clean.startswith("```"):
        first_newline = diff_clean.find("\n")
        if first_newline != -1:
            diff_clean = diff_clean[first_newline + 1 :]
        if diff_clean.endswith("```"):
            diff_clean = diff_clean[:-3].rstrip()

    lines = diff_clean.split("\n")
    hunks: list[list[tuple[str, str]]] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip file headers
        if line.startswith("---") or line.startswith("+++"):
            i += 1
            continue

        # Parse hunk header - extract lines but ignore line numbers
        if line.startswith("@@"):
            i += 1

            # Collect hunk lines
            hunk_lines: list[tuple[str, str]] = []
            while i < len(lines):
                if lines[i].startswith("@@") or lines[i].startswith("---"):
                    break

                if lines[i].startswith("-"):
                    hunk_lines.append(("-", lines[i][1:]))
                elif lines[i].startswith("+"):
                    hunk_lines.append(("+", lines[i][1:]))
                elif lines[i].startswith(" "):
                    hunk_lines.append((" ", lines[i][1:]))
                elif lines[i] == "":
                    hunk_lines.append((" ", ""))
                else:
                    # Line without prefix - treat as context
                    hunk_lines.append((" ", lines[i]))

                i += 1

            if hunk_lines:
                hunks.append(hunk_lines)
        else:
            i += 1

    if not hunks:
        raise DiffError("No valid hunks found in diff")

    # Apply hunks using fuzzy matching on evolving document
    result = original
    warnings: list[str] = []
    for idx, hunk in enumerate(hunks, 1):
        before_text, after_text = hunk_to_before_after(hunk)

        if not before_text.strip():
            # Pure addition at end - append
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = _apply_hunk_with_fallbacks(result, before_text, after_text)
        if new_result is None:
            warnings.append(f"Hunk {idx}: could not locate context in document")
        else:
            result = new_result

    # Post-process to fix LLM-generated structural issues
    result = _fix_duplicate_sections(result)
    result = _ensure_markdown_blank_lines(result)

    return result, warnings


def _fix_duplicate_sections(text: str) -> str:
    """Remove duplicate content lines that appear close together.

    LLMs sometimes generate outputs with duplicate lines when context lines
    are incorrectly preserved alongside additions. For example:
    Original: "North America contributes 60%."
    Output:   "North America contributes 60%.\nNorth America contributes 60% ($2.52M)."

    Also handles duplicate section headers.
    """
    lines = text.split("\n")
    result: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for duplicate pattern: current line is prefix of next line
        # This handles cases where simplified version appears before expanded version
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.strip()

            # Skip if current line is a prefix of next line (excluding headers, lists, tables)
            if (
                stripped
                and next_stripped
                and not stripped.startswith("#")
                and not stripped.startswith("-")
                and not stripped.startswith("|")
                and len(stripped) > 20
                and (next_stripped.startswith(stripped[:30]) or stripped in next_stripped)
                and len(next_stripped) > len(stripped)
            ):
                # Skip this line, keep the longer/expanded version
                i += 1
                continue

        # Check for duplicate section headers
        if stripped.startswith("##"):
            # Look ahead to see if this header repeats
            found_duplicate_later = False
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].strip() == stripped:
                    # Check if there's another header between them
                    has_header_between = False
                    for k in range(i + 1, j):
                        if lines[k].strip().startswith("##"):
                            has_header_between = True
                            break
                    if has_header_between:
                        # Skip this first occurrence
                        found_duplicate_later = True
                        break

            if found_duplicate_later:
                i += 1
                continue

        result.append(line)
        i += 1

    return "\n".join(result)


def _ensure_markdown_blank_lines(text: str) -> str:
    """Ensure proper blank lines in markdown structure."""
    lines = text.split("\n")
    result: list[str] = []
    prev_line: str | None = None

    for line in lines:
        curr_strip = line.strip()

        if result and prev_line is not None:
            prev_strip = prev_line.strip()
            last_was_blank = result and result[-1].strip() == ""

            # Add blank line if missing between structural elements
            if not last_was_blank and curr_strip and prev_strip:
                need_blank = (
                    (curr_strip.startswith("#") and not prev_strip.startswith("#"))
                    or (prev_strip.startswith("#") and not curr_strip.startswith("#"))
                    or (
                        curr_strip.startswith("**")
                        and not prev_strip.startswith(("-", "*", "+", "#"))
                    )
                )
                if need_blank:
                    result.append("")

        result.append(line)
        prev_line = line

    return "\n".join(result)


@register_algorithm
class GitDiffAlgorithm(Algorithm):
    """LLM generates unified diff (git diff format) to apply changes."""

    name = "git_diff"
    description = "LLM generates unified diff format, then parsed and applied"
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

        # Generate diff
        diff_content, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        # Apply diff
        try:
            result, warnings = parse_and_apply_diff(initial, diff_content)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )
        except DiffError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

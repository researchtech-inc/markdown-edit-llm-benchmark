"""Git diff algorithm - LLM generates unified diff format."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """You are an expert at generating unified diff patches to edit markdown documents.

## Your Task
Generate a unified diff (git diff format) that implements the requested changes to the document.

## Unified Diff Format

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

USER_PROMPT = """Generate a unified diff to implement the following changes to the document.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>

Generate the unified diff. Remember:
- Use EXACT text from the original for `-` lines and context lines (copy-paste, don't paraphrase)
- Include 2-3 lines of context around changes
- Preserve original line structure (don't split single lines into multiple)

Output ONLY the diff:"""


class DiffError(Exception):
    """Raised when a diff cannot be applied."""


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

    # Clean prompt artifacts from the result
    return clean_search_replace_block("\n".join(before_lines), "\n".join(after_lines))


def parse_and_apply_diff(original: str, diff_text: str) -> str:
    """Parse unified diff and apply using context-based fuzzy matching.

    Ignores line numbers from @@ headers - uses context lines to locate changes.
    Applies hunks sequentially to evolving document state.
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
    for idx, hunk in enumerate(hunks, 1):
        before_text, after_text = hunk_to_before_after(hunk)

        if not before_text.strip():
            # Pure addition at end - append
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = replace_most_similar_chunk(result, before_text, after_text)
        if new_result is None:
            raise DiffError(f"Hunk {idx}: could not locate context in document")
        result = new_result

    return result


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
            result = parse_and_apply_diff(initial, diff_content)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )
        except Exception as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=f"Failed to apply diff: {e}",
                usage=usage,
            )

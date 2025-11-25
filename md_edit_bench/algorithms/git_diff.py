"""Git diff algorithm - LLM generates unified diff format."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """You are an expert at generating unified diff patches to edit markdown documents.

## Your Task
Generate a unified diff (git diff format) that implements the requested changes to the document.

## Unified Diff Format

The diff format uses:
- `---` and `+++` lines to indicate the original and modified file
- `@@ -start,count +start,count @@` hunk headers
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

Example - changing "Sales grew 12%" to "Sales grew 12%, totaling $1.1M":

WRONG:
```diff
 Sales grew 12%
+Sales grew 12%, totaling $1.1M
```

CORRECT:
```diff
-Sales grew 12%
+Sales grew 12%, totaling $1.1M
```

## CRITICAL RULES

1. **Use exact line content**: The `-` lines and context lines MUST match the EXACT text from the original document, character for character.

2. **Include context**: Each hunk should include 3 lines of unchanged context before and after the changes.

3. **Preserve formatting**: Keep the exact whitespace, indentation, and line breaks from the original.

4. **Small focused hunks**: Make multiple small hunks rather than one large hunk when changes are in different parts of the document.

5. **Line numbers are best-effort**: Include @@ headers with approximate line numbers, but the context lines are what really matter for locating changes.

## Output Format
Output ONLY the unified diff. No explanations, no markdown code blocks around it. Just the raw diff starting with `--- a/` line."""

USER_PROMPT = """Generate a unified diff to implement the following changes to the document.

## ORIGINAL DOCUMENT
```
{initial}
```

## REQUESTED CHANGES
{changes}

Generate the unified diff. Remember:
- Use EXACT text from the original for `-` lines and context lines (copy-paste, don't paraphrase)
- Include 3 lines of context around changes - context is what matters for locating changes

Output ONLY the diff:"""


def parse_and_apply_diff(original: str, diff_text: str) -> str:
    """Parse unified diff and apply it to original content."""
    # Clean up diff text - remove markdown code blocks if present
    diff_clean = diff_text.strip()
    if diff_clean.startswith("```"):
        first_newline = diff_clean.find("\n")
        if first_newline != -1:
            diff_clean = diff_clean[first_newline + 1 :]
        if diff_clean.endswith("```"):
            diff_clean = diff_clean[:-3].rstrip()

    lines = diff_clean.split("\n")
    original_lines = original.split("\n")
    result_lines = original_lines.copy()
    offset = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip file headers
        if line.startswith("---") or line.startswith("+++"):
            i += 1
            continue

        # Parse hunk header
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                i += 1
                continue

            old_start = int(match.group(1)) - 1  # Convert to 0-indexed
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

            # Apply hunk
            pos = old_start + offset
            new_section: list[str] = []
            remove_count = 0
            add_count = 0

            for line_type, content in hunk_lines:
                if line_type == " ":
                    new_section.append(content)
                elif line_type == "-":
                    remove_count += 1
                elif line_type == "+":
                    new_section.append(content)
                    add_count += 1

            # Calculate end position
            context_and_remove = sum(1 for t, _ in hunk_lines if t in (" ", "-"))
            end_pos = pos + context_and_remove

            # Replace section
            result_lines = result_lines[:pos] + new_section + result_lines[end_pos:]

            # Update offset
            offset += add_count - remove_count
        else:
            i += 1

    return "\n".join(result_lines)


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

"""Unified diff with explicit [CTX]/[DEL]/[ADD] tags for clearer LLM guidance."""

from __future__ import annotations

import re

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """# File editing rules:

Use a unified diff format with explicit tags to mark each line:
- [CTX] for context lines (unchanged)
- [DEL] for lines to delete
- [ADD] for lines to add

Format:
```diff
--- a/document.md
+++ b/document.md
@@
[CTX] context line that stays unchanged
[DEL] line to remove
[ADD] line to add
@@
```

Example - editing multiple list items in one hunk:
```diff
@@
[CTX] The focus will be on:
[CTX]
[DEL] - Item one
[DEL] - Item two
[DEL] - Item three
[ADD] - Item one (with details)
[ADD] - Item two (with details)
[ADD] - Item three (with details)
[CTX]
[CTX] ## Next Section
@@
```

Critical rules:
1. Copy [CTX] and [DEL] lines EXACTLY from the original - character-for-character
2. If lines in the original have NO blank line between them, do NOT add blank lines in your diff
3. Group consecutive line changes into ONE hunk - do not split them
4. Only start a new @@ hunk when jumping to a different section
5. Match line breaks precisely - one line in original = one [CTX]/[DEL] line in diff"""

SYSTEM_PROMPT = f"""Act as an expert software developer.
Always use best practices when coding.
Respect and use existing conventions, libraries, etc that are already present in the code base.

Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

For each file that needs to be changed, write out the changes using a tagged unified diff format.

{FORMAT_SPECIFICATION}"""

USER_PROMPT = f"""Here is the current document:

<original_document>
{{initial}}
</original_document>

Please make these changes:

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}

IMPORTANT: Before generating the diff:
1. Read the original document carefully and note exactly how lines are formatted
2. Check if consecutive lines have blank lines between them or not
3. When creating [CTX] and [DEL] lines, copy the text EXACTLY - including line breaks
4. Do NOT insert blank lines where none exist in the original

Provide the changes as a tagged unified diff in a ```diff fenced code block."""


class TaggedUdiffError(Exception):
    """Error parsing or applying tagged unified diff."""


def parse_tagged_udiff(diff_text: str) -> list[list[tuple[str, str]]]:
    """Parse tagged unified diff into hunks.

    Args:
        diff_text: Raw diff text from LLM

    Returns:
        List of hunks, where each hunk is a list of (op, content) tuples.
        op is " " for CTX, "-" for DEL, "+" for ADD.
    """
    if not diff_text.endswith("\n"):
        diff_text = diff_text + "\n"

    lines = diff_text.splitlines(keepends=True)
    hunks: list[list[tuple[str, str]]] = []
    current_hunk: list[tuple[str, str]] = []
    in_hunk = False
    in_diff_block = False

    for line in lines:
        # Track fenced code blocks
        if line.startswith("```diff"):
            in_diff_block = True
            continue
        if line.startswith("```") and in_diff_block:
            in_diff_block = False
            # End any open hunk when exiting diff block
            if current_hunk:
                hunks.append(current_hunk)
                current_hunk = []
                in_hunk = False
            continue

        # Skip file headers
        if line.startswith("--- ") or line.startswith("+++ "):
            continue

        # Hunk markers
        if line.strip() == "@@":
            if in_hunk:
                # End of current hunk and start of next hunk
                if current_hunk:
                    hunks.append(current_hunk)
                    current_hunk = []
                # Stay in hunk mode (don't set in_hunk = False)
            else:
                # Start of new hunk
                in_hunk = True
            continue

        # Parse tagged lines within hunks
        if in_hunk:
            stripped = line.strip()

            # Handle mixed format: LLM sometimes mixes standard diff with tagged format
            # Remove leading diff markers (+, -, or space) if followed by tags
            # Note: LLMs sometimes use wrong markers (like +[DEL]), so we remove any leading marker
            if (
                stripped
                and stripped[0] in "+-"
                and (
                    stripped[1:].startswith("[ADD]")
                    or stripped[1:].startswith("[DEL]")
                    or stripped[1:].startswith("[CTX]")
                )
            ):
                stripped = stripped[1:]  # Remove the leading +, -, or space
            elif stripped.startswith(" [CTX]"):
                stripped = stripped[1:]

            # Now handle [CTX], [DEL], [ADD] tags (with or without space after tag)
            if stripped.startswith("[CTX]"):
                # Extract content after tag, handling both [CTX] and [CTX] formats
                content = stripped[6:] if stripped.startswith("[CTX] ") else stripped[5:]
                # Add line (even if empty - represents a blank line)
                current_hunk.append((" ", content + "\n"))
            elif stripped.startswith("[DEL]"):
                content = stripped[6:] if stripped.startswith("[DEL] ") else stripped[5:]
                # Add line (even if empty - represents a blank line to delete)
                current_hunk.append(("-", content + "\n"))
            elif stripped.startswith("[ADD]"):
                content = stripped[6:] if stripped.startswith("[ADD] ") else stripped[5:]
                # Add line (even if empty - represents a blank line to add)
                current_hunk.append(("+", content + "\n"))
            elif stripped == "-":
                # Bare `-` means delete a blank line (LLM mixing standard diff format)
                current_hunk.append(("-", "\n"))
            elif stripped == "+":
                # Bare `+` means add a blank line (LLM mixing standard diff format)
                current_hunk.append(("+", "\n"))
            elif stripped:
                # Line without tag - treat as context for robustness
                current_hunk.append((" ", line))

    # Don't forget final hunk if file didn't end with @@
    if current_hunk:
        hunks.append(current_hunk)

    # Post-process hunks to remove redundant CTX lines that duplicate DEL lines
    # This handles LLMs that output both [CTX] and [DEL] for the same line
    cleaned_hunks: list[list[tuple[str, str]]] = []
    for hunk in hunks:
        cleaned_hunk: list[tuple[str, str]] = []
        i = 0
        while i < len(hunk):
            op, content = hunk[i]
            # Check if this is a CTX line followed by a DEL line with same content
            if (
                op == " "
                and i + 1 < len(hunk)
                and hunk[i + 1][0] == "-"
                and hunk[i + 1][1] == content
            ):
                # Skip the CTX line, the DEL line will be kept
                i += 1
                continue
            cleaned_hunk.append((op, content))
            i += 1
        cleaned_hunks.append(cleaned_hunk)

    return cleaned_hunks


def hunk_to_before_after(hunk: list[tuple[str, str]]) -> tuple[str, str]:
    """Convert a hunk to before and after text representations.

    Args:
        hunk: List of (op, content) tuples

    Returns:
        Tuple of (before_text, after_text)
    """
    before: list[str] = []
    after: list[str] = []

    for op, content in hunk:
        if op == " ":  # CTX
            before.append(content)
            after.append(content)
        elif op == "-":  # DEL
            before.append(content)
        elif op == "+":  # ADD
            after.append(content)

    return "".join(before), "".join(after)


def normalize_whitespace_for_matching(text: str) -> str:
    """Normalize whitespace in text to make matching more robust.

    Handles cases where LLMs split paragraphs differently than the original.
    Preserves section structure (lines starting with #) and blank line separation,
    but joins consecutive paragraph lines that aren't separated by blank lines.
    """
    lines = text.splitlines(keepends=True)
    normalized: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Keep blank lines and headers as-is
        if not line.strip() or line.startswith("#"):
            normalized.append(line)
            i += 1
            continue

        # For other lines, check if we should join with next lines
        # This handles cases where LLMs split paragraphs that should be together
        joined_line = line.rstrip("\n")
        i += 1

        while i < len(lines):
            next_line = lines[i]
            # Stop if next line is blank or starts with #
            if not next_line.strip() or next_line.startswith("#"):
                break
            # Stop if next line starts with list marker
            stripped_next = next_line.lstrip()
            if stripped_next.startswith(("-", "*")) or (
                len(stripped_next) > 2 and stripped_next[0].isdigit() and stripped_next[1] == "."
            ):
                break
            # Stop if this line or next line is a table row
            if "|" in line or "|" in next_line:
                break
            # Join the line with a space
            joined_line += " " + next_line.strip()
            i += 1

        normalized.append(joined_line + "\n")

    return "".join(normalized)


def fix_paragraph_formatting(text: str) -> str:
    """Fix paragraph formatting by joining consecutive lines that should be on the same line.

    This handles cases where LLMs split multi-sentence paragraphs into separate lines.
    Only join lines that:
    1. Are prose paragraphs (not structured content)
    2. End with ". " (period space) indicating sentence continuation
    3. Next line doesn't look like a new paragraph or structure
    """
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Keep blank lines as-is
        if not line.strip():
            result.append(line)
            i += 1
            continue

        # Keep headers, list items, and table rows as-is
        stripped = line.lstrip()
        if (
            stripped.startswith("#")
            or stripped.startswith(("-", "*", "**"))
            or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] == ".")
            or "|" in line
        ):
            result.append(line)
            i += 1
            continue

        # Check if this line should be joined with the next
        # Only join if:
        # 1. Current line ends with ". " (period followed by space when rstripped and looking at original)
        # 2. Next line is also a paragraph line (not a structure)
        # 3. They form a natural continuation
        current_line = line.rstrip("\n")

        # Don't try to join if line doesn't end with period or has special formatting
        if not current_line.endswith(".") or ":" in current_line:
            result.append(line)
            i += 1
            continue

        # Look ahead to see if we should join
        if i + 1 < len(lines):
            next_line = lines[i + 1]

            # Don't join if next line is blank or structural
            if not next_line.strip():
                result.append(line)
                i += 1
                continue

            next_stripped = next_line.lstrip()
            if (
                next_stripped.startswith("#")
                or next_stripped.startswith(("-", "*", "**"))
                or (
                    len(next_stripped) > 2
                    and next_stripped[0].isdigit()
                    and next_stripped[1] == "."
                )
                or "|" in next_line
                or ":" in next_line  # Don't join with definition-like lines
            ):
                result.append(line)
                i += 1
                continue

            # Check if they should be joined: next line starts with capital and looks like a sentence continuation
            if next_stripped and next_stripped[0].isupper() and len(next_stripped.split()) > 3:
                # Join them
                result.append(current_line + " " + next_line.lstrip())
                i += 2
                continue

        result.append(line)
        i += 1

    return "".join(result)


def apply_tagged_udiff(initial: str, hunks: list[list[tuple[str, str]]]) -> tuple[str, list[str]]:
    """Apply tagged unified diff hunks to initial document.

    Returns (result, warnings) tuple. Skipped hunks are reported as warnings.
    """
    content = initial
    warnings: list[str] = []

    for i, hunk in enumerate(hunks, 1):
        before_text, after_text = hunk_to_before_after(hunk)

        # Skip hunks with no actual changes (all CTX lines)
        if before_text == after_text:
            continue

        if not before_text.strip():
            # Appending to file (no before text)
            content = content + after_text
            continue

        # Try fuzzy matching from aider_utils
        result = replace_most_similar_chunk(content, before_text, after_text)

        # If match failed, try without blank lines
        # LLMs sometimes omit or hallucinate blank lines in context
        if result is None and ("\n\n" in before_text or "\n\n" in content):
            # Remove blank lines from search pattern and content for matching
            # but keep after_text as-is to preserve intended formatting
            before_lines = [line for line in before_text.splitlines(keepends=True) if line.strip()]
            before_compact = "".join(before_lines)
            content_lines = [line for line in content.splitlines(keepends=True) if line.strip()]
            content_compact = "".join(content_lines)

            if before_compact != before_text or content_compact != content:
                result = replace_most_similar_chunk(content_compact, before_compact, after_text)

        # If still no match and content has blank lines, try with more flexible blank line handling
        # LLM might omit blank lines that exist in the original
        if result is None:
            # Normalize sequences of blank lines to single blanks for matching
            before_normalized = re.sub(r"\n\n+", "\n\n", before_text)
            content_normalized = re.sub(r"\n\n+", "\n\n", content)
            after_normalized = re.sub(r"\n\n+", "\n\n", after_text)

            if before_normalized != before_text or content_normalized != content:
                # Try matching with normalized blank lines
                result = replace_most_similar_chunk(
                    content_normalized, before_normalized, after_normalized
                )

        # If still no match, try normalizing paragraph breaks
        # LLMs sometimes split paragraphs differently than the original
        if result is None:
            # Normalize the search pattern to match how content might be formatted
            before_normalized = normalize_whitespace_for_matching(before_text)

            if before_normalized != before_text:
                # Try matching with normalized before_text against original content
                result = replace_most_similar_chunk(content, before_normalized, after_text)

        # If still no match, try removing leading spaces from each line
        # LLMs sometimes add inconsistent leading spaces
        if result is None:
            before_lines = before_text.splitlines(keepends=True)
            before_lstripped = "".join(line.lstrip(" ") for line in before_lines)
            if before_lstripped != before_text:
                result = replace_most_similar_chunk(content, before_lstripped, after_text)

        if result is None:
            warnings.append(f"Hunk {i}: could not find matching context")
        else:
            content = result

    # Post-process to fix formatting: join consecutive paragraph lines
    content = fix_paragraph_formatting(content)

    return content, warnings


@register_algorithm
class UdiffTaggedAlgorithm(Algorithm):
    """Unified diff with explicit [CTX]/[DEL]/[ADD] tags for clearer LLM guidance."""

    name = "udiff_tagged"
    description = "Unified diff with explicit [CTX]/[DEL]/[ADD] tags"
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

        # Parse and apply diffs
        hunks = parse_tagged_udiff(diff_content)

        if not hunks:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No hunks found in LLM output",
                usage=usage,
            )

        # Apply all hunks
        content, warnings = apply_tagged_udiff(initial, hunks)

        return AlgorithmResult(
            output=content,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

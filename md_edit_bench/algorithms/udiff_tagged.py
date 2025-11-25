"""Unified diff with explicit [CTX]/[DEL]/[ADD] tags for clearer LLM guidance."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """Act as an expert software developer.
Always use best practices when coding.
Respect and use existing conventions, libraries, etc that are already present in the code base.

Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

For each file that needs to be changed, write out the changes using a tagged unified diff format.

# File editing rules:

Use a unified diff format with explicit tags to mark each line:
- [CTX] for context lines (unchanged)
- [DEL] for lines to delete
- [ADD] for lines to add

Format:
```
--- a/document.md
+++ b/document.md
@@
[CTX] context line that stays unchanged
[DEL] line to remove
[ADD] line to add
@@
```

Important guidelines:
- Start each hunk with @@ on its own line
- End each hunk with @@ on its own line
- Use [CTX] to show surrounding unchanged lines for context
- Use [DEL] for every line being removed
- Use [ADD] for every line being added
- Include enough context to uniquely identify the location
- Indentation matters - preserve exact spacing
- Multiple hunks can be used for changes in different parts of the file
- CRITICAL: Preserve line structure! If multiple sentences are on ONE line in the original, keep them on ONE line in the replacement. Do not split single lines into multiple lines.

To move code within a file, use 2 hunks: 1 to delete it from its current location, 1 to insert it in the new location."""

USER_PROMPT = """Here is the current document:

<original_document>
{initial}
</original_document>

Please make these changes:

<requested_changes>
{changes}
</requested_changes>

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


def apply_tagged_udiff(initial: str, hunks: list[list[tuple[str, str]]]) -> str:
    """Apply tagged unified diff hunks to initial document.

    Args:
        initial: Initial document content
        hunks: Parsed hunks from parse_tagged_udiff

    Returns:
        Modified document

    Raises:
        TaggedUdiffError: If a hunk fails to apply
    """
    content = initial

    for hunk in hunks:
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
        if result is None:
            raise TaggedUdiffError(
                f"Hunk failed to apply - could not find matching context:\n{before_text[:200]}"
            )
        content = result

    return content


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
        try:
            hunks = parse_tagged_udiff(diff_content)

            if not hunks:
                return AlgorithmResult(
                    output=None,
                    success=False,
                    error="No hunks found in LLM output",
                    usage=usage,
                )

            # Apply all hunks
            content = apply_tagged_udiff(initial, hunks)

            return AlgorithmResult(
                output=content,
                success=True,
                error=None,
                usage=usage,
            )
        except TaggedUdiffError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )
        except Exception as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=f"Failed to apply tagged diff: {e}",
                usage=usage,
            )

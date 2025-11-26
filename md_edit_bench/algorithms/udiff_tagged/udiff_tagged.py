"""Unified diff with explicit [CTX]/[DEL]/[ADD] tags for clearer LLM guidance."""

from __future__ import annotations

from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


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


def format_failed_hunks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed hunks for the retry prompt."""
    parts: list[str] = []
    for hunk_num, before, after in failed:
        parts.append(f"Hunk {hunk_num}:")
        parts.append(f"BEFORE (expected to match):\n{before}")
        parts.append(f"AFTER (desired state):\n{after}")
        parts.append("")
    return "\n".join(parts)


def apply_tagged_udiff(
    initial: str, hunks: list[list[tuple[str, str]]]
) -> tuple[str, list[tuple[int, str, str]]]:
    """Apply tagged unified diff hunks to initial document.

    Returns (result, failed_hunks) tuple where failed_hunks contains
    (hunk_num, before_text, after_text) for hunks that couldn't be applied.
    """
    content = initial
    failed_hunks: list[tuple[int, str, str]] = []

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
        if result is None:
            failed_hunks.append((i, before_text, after_text))
        else:
            content = result

    return content, failed_hunks


class UdiffTaggedAlgorithm(Algorithm):
    """Unified diff with explicit [CTX]/[DEL]/[ADD] tags for clearer LLM guidance."""

    name = "udiff_tagged"
    description = "Unified diff with explicit [CTX]/[DEL]/[ADD] tags"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        diff_content, usage = await call_llm(model, user_prompt, system_prompt)

        # Parse and apply diffs
        hunks = parse_tagged_udiff(diff_content)

        if not hunks:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No hunks found in LLM output",
                usage=usage,
            )

        # Apply all hunks, collect failures
        content, failed_hunks = apply_tagged_udiff(initial, hunks)

        if not failed_hunks:
            return AlgorithmResult(
                output=content,
                success=True,
                error=None,
                usage=usage,
            )

        # Pass 2: Retry failed hunks with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=content,
            failed_hunks=format_failed_hunks(failed_hunks),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        retry_hunks = parse_tagged_udiff(retry_output)

        # Track which original hunks remain unrecovered
        warnings: list[str] = []

        if not retry_hunks:
            # Retry produced no hunks - all original failures become warnings
            for hunk_num, _before, _after in failed_hunks:
                warnings.append(f"Hunk {hunk_num}: failed and retry produced no fix")
        else:
            # Apply retry hunks, track failures
            retry_failed_count = 0
            for hunk in retry_hunks:
                before_text, after_text = hunk_to_before_after(hunk)
                new_result = replace_most_similar_chunk(content, before_text, after_text)
                if new_result is None:
                    retry_failed_count += 1
                else:
                    content = new_result

            # If retry returned fewer hunks than failures, or some retry hunks failed,
            # report the unrecovered count as warnings
            unrecovered = len(failed_hunks) - (len(retry_hunks) - retry_failed_count)
            if unrecovered > 0:
                warnings.append(
                    f"{unrecovered} hunk(s) unrecovered after retry "
                    f"(original failures: {[h[0] for h in failed_hunks]})"
                )

        return AlgorithmResult(
            output=content,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

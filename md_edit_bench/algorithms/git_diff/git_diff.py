"""Git diff algorithm - LLM generates unified diff format."""

from __future__ import annotations

from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class DiffError(Exception):
    """Raised when a diff cannot be applied."""


def format_failed_hunks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed hunks for the retry prompt."""
    parts: list[str] = []
    for hunk_num, before, after in failed:
        parts.append(f"Hunk {hunk_num}:")
        parts.append(f"BEFORE:\n{before}")
        parts.append(f"AFTER:\n{after}")
        parts.append("")
    return "\n".join(parts)


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


def parse_hunks(diff_text: str) -> list[list[tuple[str, str]]]:
    """Parse unified diff into hunks."""
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

    return hunks


def parse_and_apply_diff(
    original: str, diff_text: str
) -> tuple[str, list[str], list[tuple[int, str, str]]]:
    """Parse unified diff and apply using context-based fuzzy matching.

    Ignores line numbers from @@ headers - uses context lines to locate changes.
    Applies hunks sequentially to evolving document state.

    Returns (result, warnings, failed_hunks) tuple.
    failed_hunks contains (hunk_num, before_text, after_text) for failed applications.
    Raises DiffError only if no hunks found.
    """
    hunks = parse_hunks(diff_text)

    # Apply hunks using fuzzy matching on evolving document
    result = original
    warnings: list[str] = []
    failed_hunks: list[tuple[int, str, str]] = []
    for idx, hunk in enumerate(hunks, 1):
        before_text, after_text = hunk_to_before_after(hunk)

        if not before_text.strip():
            # Pure addition at end - append
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = replace_most_similar_chunk(result, before_text, after_text)
        if new_result is None:
            warnings.append(f"Hunk {idx}: could not locate context in document")
            failed_hunks.append((idx, before_text, after_text))
        else:
            result = new_result

    return result, warnings, failed_hunks


class GitDiffAlgorithm(Algorithm):
    """LLM generates unified diff (git diff format) to apply changes."""

    name = "git_diff"
    description = "LLM generates unified diff format, then parsed and applied"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        diff_content, usage = await call_llm(model, user_prompt, system_prompt)

        # Apply diff
        try:
            result, warnings, failed_hunks = parse_and_apply_diff(initial, diff_content)
        except DiffError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

        # If no failures, return result
        if not failed_hunks:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Pass 2: Retry failed hunks with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_hunks=format_failed_hunks(failed_hunks),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        # Apply retry hunks
        try:
            retry_hunks = parse_hunks(retry_output)
            retry_result, _retry_warnings, retry_failed = parse_and_apply_diff(result, retry_output)
            result = retry_result

            # Calculate unrecovered failures
            successful_retries = len(retry_hunks) - len(retry_failed)
            unrecovered = len(failed_hunks) - successful_retries

            final_warnings: list[str] = []
            if unrecovered > 0:
                final_warnings.append(
                    f"{unrecovered} hunk(s) unrecovered after retry "
                    f"(original failures: {[h[0] for h in failed_hunks]})"
                )

            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=final_warnings,
            )

        except DiffError:
            # Retry produced no valid hunks - all original failures remain as warnings
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

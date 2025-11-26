"""Codex patch algorithm - LLM generates OpenAI Codex/GPT-4.1 patch format."""

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


class PatchError(Exception):
    """Raised when patch cannot be parsed or applied."""


PATCH_MARKERS = {"*** Begin Patch", "*** End Patch", "*** End of File"}


def parse_codex_patch(patch_text: str) -> list[tuple[str, str]]:
    """Parse Codex patch into (before_text, after_text) sections for fuzzy matching.

    Handles both anchor-based (@@ anchor text) and unified diff (@@ -X,Y +A,B @@) formats.
    """
    lines = patch_text.split("\n")

    start_idx = 0
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("*** Begin Patch"):
            start_idx = i + 1
        elif line.strip() == "*** End Patch":
            end_idx = i
            break

    if start_idx == 0 and not any(line.strip().startswith("@@") for line in lines):
        raise PatchError("Missing '*** Begin Patch' marker")

    sections: list[tuple[str, str]] = []
    i = start_idx

    while i < end_idx:
        line = lines[i].strip()

        if not line or line in PATCH_MARKERS or line.startswith("*** Update File:"):
            i += 1
            continue

        if line.startswith("@@"):
            anchor_line = lines[i]

            # Check if this is unified diff format (@@ -X,Y +A,B @@) vs anchor format (@@ anchor text)
            # Unified diff has numbers after @@, anchor has text
            is_unified_diff = False
            if "@@" in anchor_line[2:]:
                # Has closing @@, likely unified diff
                is_unified_diff = True
            elif anchor_line[2:].strip() and anchor_line[2:].strip()[0].isdigit():
                # Starts with digit after @@, likely unified diff line numbers
                is_unified_diff = True

            i += 1
            before_lines: list[str] = []
            after_lines: list[str] = []

            # For anchor format, the anchor provides context for locating the change
            # Include it in both BEFORE and AFTER as it's typically unchanged context
            if not is_unified_diff:
                anchor_text = anchor_line[2:].strip()
                if anchor_text:
                    before_lines.append(anchor_text)
                    after_lines.append(anchor_text)

            # Collect the +/- lines first to determine if anchor is being replaced
            plus_lines: list[str] = []
            minus_lines: list[str] = []
            context_lines: list[str] = []

            while i < end_idx:
                if i >= len(lines):
                    break

                line = lines[i]
                stripped = line.strip()

                if stripped.startswith("@@") or stripped in PATCH_MARKERS:
                    break

                i += 1

                if stripped in PATCH_MARKERS:
                    continue

                if line.startswith("+"):
                    content = line[1:]
                    if content.strip() not in PATCH_MARKERS:
                        plus_lines.append(content)
                elif line.startswith("-"):
                    content = line[1:]
                    minus_lines.append(content)
                elif line.startswith(" "):
                    content = line[1:]
                    context_lines.append(content)
                else:
                    # Line with no prefix - treat as context
                    context_lines.append(line)

            # Determine if anchor is being replaced by checking if first + line is similar
            # to the anchor (indicating the LLM put the "before" text as anchor)
            anchor_is_replaced = False
            if not is_unified_diff and before_lines and plus_lines:
                # Check if first plus line starts similarly to anchor (likely a replacement)
                anchor_words = set(before_lines[0][:50].lower().split())
                first_plus_words = set(plus_lines[0][:50].lower().split())
                # If >50% word overlap, likely the anchor is being replaced
                if anchor_words and first_plus_words:
                    overlap = len(anchor_words & first_plus_words) / len(anchor_words)
                    if overlap > 0.5:
                        anchor_is_replaced = True

            # Build before/after considering anchor replacement
            # Only include anchor in AFTER if it's not being replaced
            if anchor_is_replaced and not is_unified_diff:
                # Clear after_lines since anchor shouldn't be there
                after_lines = []

            for line in minus_lines:
                before_lines.append(line)
            for line in context_lines:
                before_lines.append(line)
                after_lines.append(line)
            for line in plus_lines:
                after_lines.append(line)

            if before_lines or after_lines:
                # Build strings: each line in the list represents a line in the document
                # A blank line is represented as '' in the list
                # Special case: a single [''] represents one blank line = '\n'
                before_str = "\n" if before_lines == [""] else "\n".join(before_lines)
                after_str = "\n" if after_lines == [""] else "\n".join(after_lines)

                before_clean, after_clean = clean_search_replace_block(before_str, after_str)
                sections.append((before_clean, after_clean))
        else:
            i += 1

    return sections


def apply_codex_patch(
    original: str, patch_text: str
) -> tuple[str, list[tuple[int, str, str]], list[str]]:
    """Parse and apply Codex patch using fuzzy matching on evolving document.

    Returns (result, failed_sections, warnings) tuple.
    - failed_sections: list of (idx, before_text, after_text) for sections that couldn't be applied
    - warnings: list of warning messages for tracking
    Raises PatchError only if no sections found or missing markers.
    """
    sections = parse_codex_patch(patch_text)

    if not sections:
        raise PatchError("No valid patch sections found")

    result = original
    failed_sections: list[tuple[int, str, str]] = []
    warnings: list[str] = []
    for idx, (before_text, after_text) in enumerate(sections, 1):
        # Skip fuzzy matching for insufficient context (empty or single newline)
        # These sections are appended to the end
        if not before_text or before_text in ("\n", "\n\n"):
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = replace_most_similar_chunk(result, before_text, after_text)
        if new_result is None:
            failed_sections.append((idx, before_text, after_text))
            warnings.append(f"Section {idx}: could not locate context in document")
        else:
            result = new_result

    return result, failed_sections, warnings


def format_failed_sections(failed: list[tuple[int, str, str]]) -> str:
    """Format failed sections for the retry prompt."""
    parts: list[str] = []
    for section_num, before, after in failed:
        parts.append(f"Section {section_num}:")
        parts.append(f"BEFORE:\n{before}")
        parts.append(f"AFTER:\n{after}")
        parts.append("")
    return "\n".join(parts)


class CodexPatchAlgorithm(Algorithm):
    """LLM generates OpenAI Codex/GPT-4.1 patch format, then parsed and applied."""

    name = "codex_patch"
    description = "OpenAI Codex/GPT-4.1 patch format with anchor-based hunks"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        patch_text, usage = await call_llm(model, user_prompt, system_prompt)

        try:
            result, failed_sections, warnings = apply_codex_patch(initial, patch_text)
        except PatchError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

        if not failed_sections:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )

        # Pass 2: Retry failed sections with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_sections=format_failed_sections(failed_sections),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        try:
            retry_result, retry_failed, _retry_warnings = apply_codex_patch(result, retry_output)
            result = retry_result
        except PatchError:
            # Retry produced no valid sections - all original failures become warnings
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Track unrecovered sections
        final_warnings: list[str] = []
        if retry_failed:
            # Some retry sections also failed
            unrecovered = len(failed_sections) - (
                len(parse_codex_patch(retry_output)) - len(retry_failed)
            )
            if unrecovered > 0:
                final_warnings.append(
                    f"{unrecovered} section(s) unrecovered after retry "
                    f"(original failures: {[s[0] for s in failed_sections]})"
                )

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=final_warnings,
        )

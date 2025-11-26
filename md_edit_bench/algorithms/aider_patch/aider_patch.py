"""Aider patch algorithm - LLM generates V4A diff format (Aider's patch format)."""

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


# Format markers that should never appear as content
PATCH_MARKERS = {"*** Begin Patch", "*** End Patch", "*** End of File"}


def parse_sections(patch_text: str) -> list[tuple[str, str]]:
    """Parse patch into (before_text, after_text) sections for fuzzy matching."""
    lines = patch_text.split("\n")

    # Find patch boundaries
    start_idx = 0
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("*** Begin Patch"):
            start_idx = i + 1
        elif line.strip() == "*** End Patch":
            end_idx = i
            break

    # If no markers found, check if it looks like a patch
    if start_idx == 0 and not any(line.strip().startswith("@@") for line in lines):
        raise PatchError("Missing '*** Begin Patch' marker")

    sections: list[tuple[str, str]] = []
    i = start_idx

    while i < end_idx:
        line = lines[i].strip()

        # Skip blank lines and format markers
        if not line or line in PATCH_MARKERS:
            i += 1
            continue

        # Start of a section
        if line.startswith("@@"):
            i += 1
            before_lines: list[str] = []
            after_lines: list[str] = []

            while i < end_idx:
                if i >= len(lines):
                    break

                line = lines[i]
                stripped = line.strip()

                # Check for section terminators
                if stripped.startswith("@@") or stripped in PATCH_MARKERS:
                    break

                i += 1

                # Skip format markers that LLM incorrectly added as content
                if stripped in PATCH_MARKERS:
                    continue

                # Parse line type
                if line.startswith("+"):
                    # Filter out markers added as +content
                    content = line[1:]
                    if content.strip() not in PATCH_MARKERS:
                        after_lines.append(content)
                elif line.startswith("-"):
                    content = line[1:]
                    before_lines.append(content)
                    # Deletions don't go to after
                elif line.startswith(" "):
                    content = line[1:]
                    before_lines.append(content)
                    after_lines.append(content)
                elif line.strip() == "":
                    # Blank line is context
                    before_lines.append("")
                    after_lines.append("")
                # Skip lines without valid prefix

            if before_lines or after_lines:
                # Clean prompt artifacts from parsed sections
                before_clean, after_clean = clean_search_replace_block(
                    "\n".join(before_lines), "\n".join(after_lines)
                )
                sections.append((before_clean, after_clean))
        else:
            i += 1

    return sections


def apply_patch(
    original: str, patch_text: str
) -> tuple[str, list[str], list[tuple[int, str, str]]]:
    """Parse and apply patch using fuzzy matching on evolving document.

    Returns (result, warnings, failed_sections) tuple.
    Failed sections contain (section_num, before_text, after_text).
    Raises PatchError only if no sections found or missing markers.
    """
    sections = parse_sections(patch_text)

    if not sections:
        raise PatchError("No valid patch sections found")

    result = original
    warnings: list[str] = []
    failed_sections: list[tuple[int, str, str]] = []

    for idx, (before_text, after_text) in enumerate(sections, 1):
        if not before_text.strip():
            # Pure addition - append to end
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = replace_most_similar_chunk(result, before_text, after_text)
        if new_result is None:
            warnings.append(f"Section {idx}: could not locate context in document")
            failed_sections.append((idx, before_text, after_text))
        else:
            result = new_result

    return result, warnings, failed_sections


def format_failed_sections(failed: list[tuple[int, str, str]]) -> str:
    """Format failed sections for the retry prompt."""
    parts: list[str] = []
    for section_num, before_text, after_text in failed:
        parts.append(f"Section {section_num}:")
        parts.append(f"BEFORE (context and deletions):\n{before_text}")
        parts.append(f"AFTER (additions and replacements):\n{after_text}")
        parts.append("")
    return "\n".join(parts)


class AiderPatchAlgorithm(Algorithm):
    """LLM generates Aider V4A patch format, then parsed and applied."""

    name = "aider_patch"
    description = "LLM generates Aider V4A patch format, then parsed and applied"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        patch_text, usage = await call_llm(model, user_prompt, system_prompt)

        try:
            result, warnings, failed_sections = apply_patch(initial, patch_text)
        except PatchError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

        # If no failures, return immediately
        if not failed_sections:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )

        # Pass 2: Retry failed sections with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_sections=format_failed_sections(failed_sections),
        )
        retry_patch_text, retry_usage = await call_llm(model, retry_prompt, system_prompt)
        usage = usage + retry_usage

        try:
            retry_result, _retry_warnings, retry_failed = apply_patch(result, retry_patch_text)
            result = retry_result

            # Track unrecovered sections as warnings
            if retry_failed:
                warnings.append(
                    f"{len(retry_failed)} section(s) unrecovered after retry "
                    f"(original failures: {[s[0] for s in failed_sections]})"
                )
        except PatchError:
            # Retry produced no valid sections - all original failures remain
            warnings.append(
                f"{len(failed_sections)} section(s) failed and retry produced no fix "
                f"(failed sections: {[s[0] for s in failed_sections]})"
            )

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

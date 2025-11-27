"""Partial rewrite algorithm - LLM outputs full document with ... for unchanged blocks."""

from __future__ import annotations

from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)

ELLIPSIS = "..."

# Unicode characters that LLMs sometimes use instead of ASCII equivalents
UNICODE_REPLACEMENTS = {
    "\u2011": "-",  # non-breaking hyphen
    "\u2010": "-",  # hyphen
    "\u2212": "-",  # minus sign
}


def normalize_unicode(text: str) -> str:
    """Replace common Unicode characters with ASCII equivalents."""
    for unicode_char, ascii_char in UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def find_first(lines: list[str], target: str, start: int = 0) -> int | None:
    """Find first occurrence of target line at or after start position."""
    for i in range(start, len(lines)):
        if lines[i] == target:
            return i
    return None


def expand_document(original: str, output: str) -> tuple[str, str | None]:
    """Expand ... markers in output using content from original.

    When LLM outputs:
        first_line
        ...
        last_line

    This represents an unchanged block where content between first_line
    and last_line is skipped. We expand by inserting the skipped content
    from the original document.

    Returns:
        Tuple of (expanded_document, error_message_or_none)
    """
    orig_lines = original.split("\n")
    out_lines = output.split("\n")
    result: list[str] = []
    search_start = 0  # Start position for searching in original

    i = 0
    while i < len(out_lines):
        line = out_lines[i]

        if line.strip() == ELLIPSIS:
            if not result:
                return original, "Ellipsis at start without preceding line"
            if i + 1 >= len(out_lines):
                return original, "Ellipsis at end without following line"

            before_line = result[-1]
            after_line = out_lines[i + 1]

            before_pos = find_first(orig_lines, before_line, search_start)
            if before_pos is None:
                return original, f"Anchor not found in original: {before_line[:60]}"

            after_pos = find_first(orig_lines, after_line, before_pos + 1)
            if after_pos is None:
                return original, f"Anchor not found in original: {after_line[:60]}"

            for j in range(before_pos + 1, after_pos):
                result.append(orig_lines[j])

            # Update search_start to after the after_line position
            search_start = after_pos + 1
            i += 1
        else:
            result.append(line)
            i += 1

    return "\n".join(result), None


class PartialRewriteAlgorithm(Algorithm):
    """LLM outputs full document with ... to skip large unchanged blocks."""

    name = "partial_rewrite"
    description = "Outputs full document with ... for unchanged content blocks"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        output, usage = await call_llm(model, user_prompt, system_prompt)
        output = normalize_unicode(output)

        result, error = expand_document(initial, output)

        return AlgorithmResult(
            output=result,
            success=True,
            error=error,
            usage=usage,
        )
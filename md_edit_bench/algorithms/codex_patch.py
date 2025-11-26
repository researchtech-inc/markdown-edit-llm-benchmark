"""Codex patch algorithm - LLM generates OpenAI Codex/GPT-4.1 patch format."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
    strip_quoted_wrapping,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """## Patch Format

Enclose your response in patch markers:
```
*** Begin Patch
*** Update File: document.md
[one or more change blocks]
*** End Patch
```

Each change block contains lines with EXACTLY one prefix character:
- ` ` (space) = context line (unchanged)
- `-` (minus) = remove this line
- `+` (plus) = add this line

To separate multiple change blocks in different parts of the document, put a blank line between them.

## Critical Rules

1. **Every line MUST have a space, minus, or plus prefix**. No unprefixed lines.

2. **Each document line appears exactly once**. If changing a line, show it ONLY as `-` (old) and `+` (new), NOT as context too.

3. **Include 2-3 context lines** before and after EACH change for anchoring.

4. **Separate distant changes** with a blank line to create multiple change blocks.

## Example: Multiple changes

Original:
```
## Executive Summary

Our Q3 sales exceeded expectations.

## Key Highlights

- Revenue: $4.2M
- Customers: +23%

## Regional Performance
```

CORRECT patch (note: blank line separates the two change blocks):
```
*** Begin Patch
*** Update File: document.md
 ## Executive Summary

 Our Q3 sales exceeded expectations.
+
+### Performance Comparison
+
+Details here.

 ## Key Highlights

 - Revenue: $4.2M
 - Customers: +23%
+
+### Revenue Breakdown
+
+More details.

 ## Regional Performance
*** End Patch
```"""

SYSTEM_PROMPT = f"""You are an expert document editor. Generate patches to edit markdown documents.

{FORMAT_SPECIFICATION}

Output ONLY the patch. No explanations."""

USER_PROMPT = f"""Generate a patch to implement the following changes to the document.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}

Output the patch:"""


class PatchError(Exception):
    """Raised when patch cannot be parsed or applied."""


PATCH_MARKERS = {"*** Begin Patch", "*** End Patch", "*** End of File"}


def parse_codex_patch(patch_text: str) -> list[tuple[str, str]]:
    """Parse patch into (before_text, after_text) sections for fuzzy matching."""
    # Strip markdown fences if present
    patch_text = strip_quoted_wrapping(patch_text)
    lines = patch_text.split("\n")

    start_idx = 0
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("*** Begin Patch"):
            start_idx = i + 1
        elif line.strip() == "*** End Patch":
            end_idx = i
            break

    if start_idx == 0:
        raise PatchError("Missing '*** Begin Patch' marker")

    sections: list[tuple[str, str]] = []

    # Pre-process to detect bullet point patterns
    # When we see "- Item" followed eventually by "+ - Item (details)", treat as bullet removal
    # Build a set of line indices that need bullet markers prepended
    lines_needing_bullets: set[int] = set()
    for i in range(start_idx, end_idx):
        if i >= len(lines):
            break
        line = lines[i]
        stripped = line.strip()

        # Check if this is a removal line that looks like it might be missing bullet marker
        if (
            line.startswith("-")
            and not stripped.startswith("---")
            and not stripped.startswith("--")
        ):
            content = line[1:]
            # Look ahead for a matching + line with bullet
            if content and content[0] in " \t":
                # Scan ahead for + lines
                for j in range(i + 1, min(i + 10, end_idx)):
                    if lines[j].startswith("+"):
                        next_content = lines[j][1:]
                        if next_content and next_content[0] in " \t":
                            stripped_next = next_content.lstrip()
                            if stripped_next and stripped_next[0] in "-*+":
                                # Found a + line with bullet marker
                                lines_needing_bullets.add(i)
                                break
                            elif stripped_next and stripped_next[0].isdigit():
                                # Check for numbered list
                                for k, ch in enumerate(stripped_next):
                                    if ch == ".":
                                        if (
                                            k < len(stripped_next) - 1
                                            and stripped_next[k + 1] == " "
                                        ):
                                            # Found numbered list
                                            lines_needing_bullets.add(i)
                                            break
                                        break
                                    if not ch.isdigit():
                                        break
                                if i in lines_needing_bullets:
                                    break
                        break
                    elif not lines[j].startswith("-"):
                        # Not a continuation of removals
                        break

    # Collect all lines into one big before/after
    before_lines: list[str] = []
    after_lines: list[str] = []

    i = start_idx
    while i < end_idx:
        if i >= len(lines):
            break

        line = lines[i]
        stripped = line.strip()

        # Skip markers and file headers
        if stripped in PATCH_MARKERS or stripped.startswith("*** Update File:"):
            i += 1
            continue

        # Empty lines are treated as context (both before and after)
        if not stripped:
            before_lines.append("")
            after_lines.append("")
            i += 1
            continue

        # Skip @@ lines if present (for backward compat)
        if stripped.startswith("@@"):
            i += 1
            continue

        i += 1

        # Check if this is a blank line separator between sections
        # Accept lines that are only whitespace (space prefix with no content)
        if not stripped and line and line[0] == " ":
            # Blank line with just space prefix - section separator
            if before_lines or after_lines:
                before_str = "\n" if before_lines == [""] else "\n".join(before_lines)
                after_str = "\n" if after_lines == [""] else "\n".join(after_lines)
                before_clean, after_clean = clean_search_replace_block(before_str, after_str)
                sections.append((before_clean, after_clean))
                before_lines = []
                after_lines = []
            continue

        # Process based on prefix
        if line.startswith("+"):
            # Added line - only in after
            content = line[1:]
            after_lines.append(content)
        elif line.startswith("-"):
            # Removed line - only in before
            content = line[1:]
            # If this line needs a bullet marker prepended (from preprocessing), add it
            if i - 1 in lines_needing_bullets:  # i-1 because we already incremented i
                content = "-" + content
            # Skip if this would create consecutive empty lines (common LLM error)
            if not (content == "" and before_lines and before_lines[-1] == ""):
                before_lines.append(content)
        elif line.startswith("#"):
            # Markdown heading without space prefix - treat as context
            before_lines.append(line)
            after_lines.append(line)
        elif line.startswith(" "):
            # Context line - in both before and after
            # Strip leading whitespace prefix (may be more than one space)
            content = line.lstrip(" ")
            before_lines.append(content)
            after_lines.append(content)
        elif before_lines or after_lines:
            # Unprefixed line - might be a section break or mistake
            # Treat current accumulated content as a section, then start fresh
            before_str = "\n" if before_lines == [""] else "\n".join(before_lines)
            after_str = "\n" if after_lines == [""] else "\n".join(after_lines)
            before_clean, after_clean = clean_search_replace_block(before_str, after_str)
            sections.append((before_clean, after_clean))
            before_lines = []
            after_lines = []

    # Don't forget the last section
    if before_lines or after_lines:
        before_str = "\n" if before_lines == [""] else "\n".join(before_lines)
        after_str = "\n" if after_lines == [""] else "\n".join(after_lines)
        before_clean, after_clean = clean_search_replace_block(before_str, after_str)
        sections.append((before_clean, after_clean))

    # Deduplicate consecutive identical lines in each section (common LLM error)
    deduped_sections: list[tuple[str, str]] = []
    for before_text, after_text in sections:
        before_lines = before_text.split("\n")
        after_lines = after_text.split("\n")

        # Remove consecutive duplicates (even with blank lines in between)
        before_deduped = [before_lines[0]] if before_lines else []
        for line in before_lines[1:]:
            # Find last non-blank line to compare against
            last_nonblank_idx = len(before_deduped) - 1
            while last_nonblank_idx >= 0 and not before_deduped[last_nonblank_idx].strip():
                last_nonblank_idx -= 1

            # Add if different from last non-blank line, or if current line is blank
            if (
                not line.strip()
                or last_nonblank_idx < 0
                or line != before_deduped[last_nonblank_idx]
            ):
                before_deduped.append(line)

        after_deduped = [after_lines[0]] if after_lines else []
        for line in after_lines[1:]:
            last_nonblank_idx = len(after_deduped) - 1
            while last_nonblank_idx >= 0 and not after_deduped[last_nonblank_idx].strip():
                last_nonblank_idx -= 1

            if (
                not line.strip()
                or last_nonblank_idx < 0
                or line != after_deduped[last_nonblank_idx]
            ):
                after_deduped.append(line)

        deduped_sections.append(("\n".join(before_deduped), "\n".join(after_deduped)))

    return deduped_sections


def normalize_line_breaks(text: str) -> str:
    """Normalize line breaks by joining lines within paragraphs.

    LLMs sometimes wrap long lines differently than the original.
    This normalizes both texts so they can be compared despite different wrapping.
    """
    lines = text.split("\n")
    normalized: list[str] = []

    for line in lines:
        stripped = line.strip()

        # If this is a blank line or special element, keep it as-is
        if not stripped or line.lstrip().startswith(("#", "-", "*", "+", ">", "|", "```")):
            # Skip consecutive blank lines (only keep one)
            if not stripped and normalized and not normalized[-1].strip():
                continue
            normalized.append(line)
        else:
            # Check if this line looks like a numbered list item
            is_numbered_list = False
            if stripped and stripped[0].isdigit():
                # Check for patterns like "1. " or "2. "
                for i, ch in enumerate(stripped):
                    if ch == ".":
                        if i < len(stripped) - 1 and stripped[i + 1] == " ":
                            is_numbered_list = True
                        break
                    if not ch.isdigit():
                        break

            # Check if line ends with a colon (like "Date:" or "Attendees:")
            ends_with_colon = stripped.endswith(":")

            # Find the last non-blank line to decide if we should join
            last_nonblank_idx = len(normalized) - 1
            while last_nonblank_idx >= 0 and not normalized[last_nonblank_idx].strip():
                last_nonblank_idx -= 1

            # If we found a non-blank line and it's not a special element, consider joining
            if last_nonblank_idx >= 0 and not normalized[last_nonblank_idx].lstrip().startswith(
                ("#", "-", "*", "+", ">", "|", "```")
            ):
                # Don't join if current line is numbered list or ends with colon
                # Don't join if previous line ended with colon
                prev_ends_with_colon = normalized[last_nonblank_idx].strip().endswith(":")
                if not is_numbered_list and not ends_with_colon and not prev_ends_with_colon:
                    # Remove the blank lines between
                    normalized = normalized[: last_nonblank_idx + 1]
                    normalized[last_nonblank_idx] += " " + stripped
                else:
                    normalized.append(line)
            else:
                normalized.append(line)

    return "\n".join(normalized)


def apply_codex_patch(original: str, patch_text: str) -> tuple[str, list[str]]:
    """Parse and apply patch using fuzzy matching on evolving document."""
    sections = parse_codex_patch(patch_text)

    if not sections:
        raise PatchError("No valid patch sections found")

    result = original
    warnings: list[str] = []
    for idx, (before_text, after_text) in enumerate(sections, 1):
        # Skip fuzzy matching for insufficient context
        if not before_text or before_text in ("\n", "\n\n"):
            result = result.rstrip("\n") + "\n" + after_text
            continue

        # Normalize line breaks to handle LLM reformatting
        before_normalized = normalize_line_breaks(before_text)
        result_normalized = normalize_line_breaks(result)
        after_normalized = normalize_line_breaks(after_text)

        new_result = replace_most_similar_chunk(
            result_normalized, before_normalized, after_normalized
        )
        if new_result is None:
            # Try finding the before_text within result by skipping initial lines
            # LLMs often omit the document title/header from the first section
            result_lines = result_normalized.split("\n")
            for skip_lines in range(min(15, len(result_lines))):
                partial_result = "\n".join(result_lines[skip_lines:])
                if before_normalized in partial_result or partial_result.startswith(
                    before_normalized.split("\n")[0]
                ):
                    # Try matching with skipped lines
                    test_result = replace_most_similar_chunk(
                        partial_result, before_normalized, after_normalized
                    )
                    if test_result is not None:
                        # Reconstruct with skipped lines
                        new_result = "\n".join(result_lines[:skip_lines]) + "\n" + test_result
                        break

        if new_result is None:
            # Last resort: try ignoring blank line differences
            # LLMs sometimes omit or add extra blank lines in context
            def remove_blanks(text: str) -> str:
                return "\n".join(line for line in text.split("\n") if line.strip())

            before_no_blanks = remove_blanks(before_normalized)
            result_no_blanks = remove_blanks(result_normalized)
            after_no_blanks = remove_blanks(after_normalized)

            test_result = replace_most_similar_chunk(
                result_no_blanks, before_no_blanks, after_no_blanks
            )
            if test_result is not None:
                # Success - we matched ignoring blank lines
                new_result = test_result

        if new_result is None:
            warnings.append(f"Section {idx}: could not locate context in document")
        else:
            result = new_result

    return result, warnings


@register_algorithm
class CodexPatchAlgorithm(Algorithm):
    """LLM generates OpenAI Codex/GPT-4.1 patch format, then parsed and applied."""

    name = "codex_patch"
    description = "OpenAI Codex/GPT-4.1 patch format with anchor-based hunks"
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

        patch_text, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        try:
            result, warnings = apply_codex_patch(initial, patch_text)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings,
            )
        except PatchError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

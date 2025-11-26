"""Aider patch algorithm - LLM generates V4A diff format (Aider's patch format)."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """## V4A Diff Format

Your response MUST be enclosed in patch markers:
*** Begin Patch
[patch content]
*** End Patch

Use this format for each change:

@@
[context lines - no prefix needed]
-[lines to remove]
+[lines to add]
[context lines - no prefix needed]
@@

## Critical Rules

1. **Context lines have NO prefix**: Regular context lines (unchanged) are written as-is without any prefix character.

2. **Lines to remove start with `-`**: Any line being removed must start with a minus sign.

3. **Lines to add start with `+`**: Any line being added must start with a plus sign.

4. **Include sufficient unique context**: Include 2-4 lines of context before and after changes. Context must be UNIQUE enough to locate the change unambiguously in the ORIGINAL document.

5. **CRITICAL - Each hunk matches the ORIGINAL**: Every @@ section must match text from the ORIGINAL document state, NOT from text that would be created by earlier hunks. All hunks are independent.

6. **Combine nearby changes**: When multiple changes are close together (within 3-4 lines), combine them into ONE @@ section. This prevents context matching issues.

7. **Separate distant changes**: Use separate @@ sections ONLY for changes that are far apart (different sections/paragraphs).

8. **Blank lines in context**: If a blank line exists in the original and is context, write it as a blank line (no prefix).

9. **Blank lines being added**: If adding a blank line, use just `+` on its own line.

## Example - Modifying text

*** Begin Patch
@@
## Q3 Results

-Sales grew 12%
+Sales grew 12%, totaling $1.1M

The team exceeded expectations.
@@
*** End Patch

## Example - Adding new section after existing content

Original document:
```
## Executive Summary
The growth was driven by enterprise.

## Key Highlights
- Revenue reached $1M
```

Patch to add Q2 vs Q3 comparison table:
*** Begin Patch
@@
## Executive Summary

The growth was driven by enterprise.

+### Q2 vs Q3 Comparison
+
+| Metric | Q2 | Q3 |
+|--------|-----|-----|
+| Revenue | $0.9M | $1M |
+
## Key Highlights
@@
*** End Patch

Note: Include the section header (## Executive Summary) BEFORE the text being changed to provide clear location context!

## Example - Replacing list items

*** Begin Patch
@@
The focus will be on:

-- Expanding the partner ecosystem
+- Expanding the partner ecosystem (targeting 15 new partnerships)
-- Launching new product features
+- Launching new product features (AI-powered analytics module)

## Conclusion
@@
*** End Patch

## BAD Example - Insufficient context (DON'T DO THIS!)

Wrong:
```
@@
- Item 3
- Item 4

+### New Section
+Content here
```

This is BAD because it's missing the section header! Correct version:
```
@@
## List Section

- Item 1
- Item 2
- Item 3
- Item 4

+### New Section
+Content here
+
## Next Section
@@
```

ALWAYS include the section header (##, ###, etc.) BEFORE any content you're changing!"""

SYSTEM_PROMPT = f"""You are an expert document editor. Generate patches in V4A diff format to edit markdown documents.

{FORMAT_SPECIFICATION}

CRITICAL: When adding content after existing text, you MUST include:
1. The section header (## or ###) that contains the existing text
2. ALL lines from that section up to where you're adding
3. The new content with + prefix
4. A few lines after to show where it ends

Output ONLY the patch. No explanations."""

USER_PROMPT = f"""Generate a V4A diff patch to implement the following changes to the document.

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


def parse_sections(patch_text: str) -> list[tuple[str, str]]:
    """Parse patch into (before_text, after_text) sections for fuzzy matching.

    V4A format rules:
    - Lines without prefix (or with space prefix) = context (appear in BOTH before AND after)
    - Lines with `-` prefix = deletion (only in before)
    - Lines with `+` prefix = addition (only in after)
    """
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
            raw_lines: list[tuple[str, str]] = []  # (line_type, content)

            # First pass: collect all lines with their types
            while i < end_idx:
                if i >= len(lines):
                    break

                line = lines[i]
                stripped = line.strip()

                # Check for section terminators
                if stripped.startswith("@@") or stripped in PATCH_MARKERS:
                    break

                i += 1

                # Skip format markers
                if stripped in PATCH_MARKERS:
                    continue

                # Parse line type
                if line.startswith("+") and (len(line) == 1 or line[1] != "+"):
                    content = line[1:]
                    if content.strip() not in PATCH_MARKERS:
                        raw_lines.append(("+", content))
                elif line.startswith("-") and (len(line) == 1 or line[1] != "-"):
                    if len(line) > 1 and line[1] == " ":
                        # Markdown list item: "- item" - treat as context
                        raw_lines.append(("=", line))
                    else:
                        # Deletion marker
                        content = line[1:]
                        raw_lines.append(("-", content))
                elif line.startswith(" "):
                    # Space prefix = context (legacy format)
                    content = line[1:]
                    raw_lines.append(("=", content))
                else:
                    # No prefix = context
                    raw_lines.append(("=", line))

            # Second pass: detect LLM errors where context lines are actually being replaced
            # Pattern: context lines followed by addition lines that expand/modify them
            # Build lists of context, deletion and addition lines for batch checking
            context_lines: list[tuple[int, str]] = []  # (index, content)
            deletion_lines: list[str] = []
            addition_lines: list[str] = []

            for idx, (line_type, content) in enumerate(raw_lines):
                if line_type == "=":
                    context_lines.append((idx, content))
                elif line_type == "-":
                    deletion_lines.append(content)
                elif line_type == "+":
                    addition_lines.append(content)

            # Check which context lines are actually replacements
            # BUT: only convert if there's no explicit deletion for the same content
            lines_to_convert: set[int] = set()
            for idx, context_content in context_lines:
                # Strip list markers and normalize for comparison
                context_stripped = context_content.lstrip("- ").strip().lower()

                # Check if this context already has an explicit deletion
                already_deleted = False
                for del_content in deletion_lines:
                    del_stripped = del_content.lstrip("- ").strip().lower()
                    if context_stripped == del_stripped or context_stripped in del_stripped:
                        already_deleted = True
                        break

                if already_deleted:
                    continue

                # Check if any addition line expands this context
                for add_content in addition_lines:
                    add_stripped = add_content.lstrip("- ").strip().lower()

                    # If context appears in addition (with possible expansion)
                    if len(context_stripped) >= 10 and (
                        context_stripped in add_stripped
                        or add_stripped.startswith(context_stripped[:30])
                    ):
                        lines_to_convert.add(idx)
                        break

            # Build corrected lines, converting marked context to deletions
            corrected_lines: list[tuple[str, str]] = []
            for idx, (line_type, content) in enumerate(raw_lines):
                if idx in lines_to_convert:
                    corrected_lines.append(("-", content))
                else:
                    corrected_lines.append((line_type, content))

            # Build before/after from corrected lines
            before_lines: list[str] = []
            after_lines: list[str] = []

            for line_type, content in corrected_lines:
                if line_type == "+":
                    # Addition - only in after
                    after_lines.append(content)
                elif line_type == "-":
                    # Deletion - only in before
                    before_lines.append(content)
                else:  # line_type == "="
                    # Context - in both
                    before_lines.append(content)
                    after_lines.append(content)

            before_text = "\n".join(before_lines)
            after_text = "\n".join(after_lines)

            if before_text.strip() or after_text.strip():
                # Clean prompt artifacts from parsed sections
                before_clean, after_clean = clean_search_replace_block(before_text, after_text)
                sections.append((before_clean, after_clean))
        else:
            i += 1

    return sections


def fuzzy_find_and_replace(original: str, before_text: str, after_text: str) -> str | None:
    """Aggressively try to find and replace text using multiple strategies.

    This handles cases where the LLM provides minimal context (e.g., just one line).
    """
    # Strategy 1: Use aider's built-in fuzzy matching
    result = replace_most_similar_chunk(original, before_text, after_text)
    if result is not None:
        return result

    # Strategy 2: If before_text is very short (1-3 lines), try to find it as a substring
    # and replace it, but only if it appears exactly once
    before_stripped = before_text.strip()
    after_stripped = after_text.strip()

    if (
        before_stripped
        and before_stripped.count("\n") <= 2
        and original.count(before_stripped) == 1
    ):
        # Text appears exactly once in the document - safe to replace
        return original.replace(before_stripped, after_stripped, 1)

    # Strategy 3: Try matching just the first and last lines (in case middle context is missing)
    before_lines = before_text.strip().split("\n")
    after_lines = after_text.strip().split("\n")

    if len(before_lines) >= 2:
        first_line = before_lines[0].strip()
        last_line = before_lines[-1].strip()

        # Find positions where first and last lines appear
        orig_lines = original.split("\n")
        for i in range(len(orig_lines)):
            if orig_lines[i].strip() == first_line:
                # Look for last_line after this
                for j in range(i + 1, min(i + 20, len(orig_lines))):
                    if orig_lines[j].strip() == last_line:
                        # Found a match! Replace lines i through j
                        new_lines = orig_lines[:i] + after_lines + orig_lines[j + 1 :]
                        return "\n".join(new_lines)

    return None


def normalize_markdown_paragraphs(text: str) -> str:
    """Normalize markdown by joining lines that belong to the same paragraph.

    In markdown, consecutive lines without blank lines between them should be
    joined into a single paragraph, unless they start with special markdown syntax
    or look like structured key-value pairs.
    """
    lines = text.split("\n")
    normalized: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is a special markdown line that should not be joined
        is_special = (
            not stripped  # blank line
            or stripped.startswith("#")  # heading
            or stripped.startswith("-")  # list item or horizontal rule
            or stripped.startswith("*")  # list item or emphasis/horizontal rule
            or stripped.startswith("+")  # list item
            or stripped.startswith("|")  # table row
            or stripped.startswith(">")  # blockquote
            or stripped.startswith("```")  # code fence
            or (
                len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] in ".)"
            )  # numbered list
            or ":" in stripped[:40]  # key-value pair like "Date: ..." or "Author: ..."
        )

        if is_special or not stripped:
            # Keep as-is
            normalized.append(line)
            i += 1
        else:
            # This is a regular paragraph line - collect consecutive lines
            paragraph_lines = [line]
            i += 1

            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                # Stop if we hit a blank line
                if not next_stripped:
                    break

                # Stop if next line is special markdown or key-value pair
                next_is_special = (
                    next_stripped.startswith("#")
                    or next_stripped.startswith("-")
                    or next_stripped.startswith("*")
                    or next_stripped.startswith("+")
                    or next_stripped.startswith("|")
                    or next_stripped.startswith(">")
                    or next_stripped.startswith("```")
                    or (
                        len(next_stripped) >= 2
                        and next_stripped[0].isdigit()
                        and next_stripped[1] in ".)"
                    )
                    or ":" in next_stripped[:40]  # key-value pair
                )

                if next_is_special:
                    break

                # Add to paragraph
                paragraph_lines.append(next_line)
                i += 1

            # Join the paragraph into a single line
            normalized.append(" ".join(pline.strip() for pline in paragraph_lines if pline.strip()))

    return "\n".join(normalized)


def remove_duplicate_sections(text: str) -> str:
    """Remove duplicate sections that may appear in the output.

    Detects when content blocks (separated by blank lines) appear multiple times
    and keeps only the first occurrence.
    """
    # Split into blocks separated by blank lines
    blocks: list[str] = []
    current_block: list[str] = []

    for line in text.split("\n"):
        if not line.strip():
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            blocks.append("")  # blank line
        else:
            current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block))

    # Track seen non-empty blocks and remove duplicates
    seen_blocks: set[str] = set()
    deduplicated: list[str] = []

    for block in blocks:
        if not block.strip():
            deduplicated.append(block)
        else:
            # Normalize for comparison (strip whitespace variations)
            normalized = "\n".join(line.strip() for line in block.split("\n") if line.strip())
            if normalized not in seen_blocks:
                seen_blocks.add(normalized)
                deduplicated.append(block)

    return "\n".join(deduplicated)


def clean_markdown_structure(text: str) -> str:
    """Clean up markdown structure issues like orphaned headers and extra blank lines."""
    lines = text.split("\n")
    cleaned: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip if this is an excessive blank line
        if not line.strip():
            # Look ahead to see if there are multiple blank lines
            blank_count = 0
            j = i
            while j < len(lines) and not lines[j].strip():
                blank_count += 1
                j += 1

            # Keep at most 2 consecutive blank lines
            if blank_count > 2:
                cleaned.append("")
                cleaned.append("")
                i = j
                continue

        # Check if this is a duplicate heading (same heading appears later with actual content)
        if line.strip().startswith("#"):
            heading = line.strip()
            # Look ahead to see if next non-blank line is another heading or if section is empty
            next_content_idx = i + 1
            while next_content_idx < len(lines) and not lines[next_content_idx].strip():
                next_content_idx += 1

            if next_content_idx < len(lines):
                next_line = lines[next_content_idx].strip()
                # If next line is a heading at same or higher level, current section is empty
                if next_line.startswith("#"):
                    current_level = len(heading) - len(heading.lstrip("#"))
                    next_level = len(next_line) - len(next_line.lstrip("#"))
                    # Check if there's a duplicate of this heading later
                    if next_level <= current_level:
                        # Look for duplicate heading
                        for k in range(next_content_idx, len(lines)):
                            if lines[k].strip() == heading:
                                # Found duplicate - skip this empty one
                                i = next_content_idx
                                continue

        cleaned.append(line)
        i += 1

    return "\n".join(cleaned)


def apply_patch(original: str, patch_text: str) -> tuple[str, list[str]]:
    """Parse and apply patch using fuzzy matching on evolving document.

    Returns (result, warnings) tuple. Skipped sections are reported as warnings.
    Raises PatchError only if no sections found or missing markers.
    """
    sections = parse_sections(patch_text)

    if not sections:
        raise PatchError("No valid patch sections found")

    result = original
    warnings: list[str] = []
    for idx, (before_text, after_text) in enumerate(sections, 1):
        if not before_text.strip():
            # Pure addition - append to end
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = fuzzy_find_and_replace(result, before_text, after_text)
        if new_result is None:
            warnings.append(f"Section {idx}: could not locate context in document")
        else:
            result = new_result

    # Post-process to fix formatting issues
    result = normalize_markdown_paragraphs(result)
    result = remove_duplicate_sections(result)

    return result, warnings


@register_algorithm
class AiderPatchAlgorithm(Algorithm):
    """LLM generates Aider V4A patch format, then parsed and applied."""

    name = "aider_patch"
    description = "LLM generates Aider V4A patch format, then parsed and applied"
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
            result, warnings = apply_patch(initial, patch_text)
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

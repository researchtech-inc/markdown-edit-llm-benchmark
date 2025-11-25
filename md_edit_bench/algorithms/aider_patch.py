"""Aider patch algorithm - LLM generates V4A diff format (Aider's patch format)."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """You are an expert document editor. Generate patches in V4A diff format to edit markdown documents.

## V4A Diff Format

Your response MUST be enclosed in patch markers:
*** Begin Patch
[patch content]
*** End Patch

Use this format for each change section:

@@
 context line (space prefix = unchanged)
-line to remove (minus prefix)
+line to add (plus prefix)
 context line
@@

## Critical Rules

1. **Context lines**: Lines starting with space must match the original text.

2. **Include context**: Include 2-3 lines before and after changes for location.

3. **Multiple changes**: Use separate @@ sections for changes in different parts.

4. **Replacing vs Adding**: Use `-` to remove old, `+` to add new.

5. **Preserve line structure**: If multiple sentences are on one line, keep them together.

## Example

*** Begin Patch
@@
 ## Q3 Results

-Sales grew 12%
+Sales grew 12%, totaling $1.1M

 The team exceeded expectations.
@@
*** End Patch

Output ONLY the patch. No explanations."""

USER_PROMPT = """Generate a V4A diff patch to implement the following changes to the document.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>

Generate the patch. Remember:
- Enclose in *** Begin Patch / *** End Patch markers
- Use @@ to mark each change section
- Context lines use space prefix, removals use -, additions use +

Output the patch:"""


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


def apply_patch(original: str, patch_text: str) -> str:
    """Parse and apply patch using fuzzy matching on evolving document."""
    sections = parse_sections(patch_text)

    if not sections:
        raise PatchError("No valid patch sections found")

    result = original
    for idx, (before_text, after_text) in enumerate(sections, 1):
        if not before_text.strip():
            # Pure addition - append to end
            result = result.rstrip("\n") + "\n" + after_text
            continue

        new_result = replace_most_similar_chunk(result, before_text, after_text)
        if new_result is None:
            raise PatchError(f"Section {idx}: could not locate context in document")
        result = new_result

    return result


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
            result = apply_patch(initial, patch_text)
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )
        except PatchError as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=str(e),
                usage=usage,
            )

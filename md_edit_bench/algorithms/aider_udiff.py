"""Aider's unified diff algorithm - context-based matching with fallback strategies."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """# File editing rules:

Return edits similar to unified diffs that `diff -U0` would produce.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.

Indentation matters in the diffs!

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

CRITICAL: Preserve line structure! If multiple sentences are on ONE line in the original, keep them on ONE line in the replacement. Do not split single lines into multiple lines.

To move code within a file, use 2 hunks: 1 to delete it from its current location, 1 to insert it in the new location."""

SYSTEM_PROMPT = f"""Act as an expert software developer.
Always use best practices when coding.
Respect and use existing conventions, libraries, etc that are already present in the code base.

Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

For each file that needs to be changed, write out the changes similar to a unified diff like `diff -U0` would produce.

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

Provide the changes as a unified diff in a ```diff fenced code block."""


def find_diffs(content: str) -> list[tuple[str | None, list[str]]]:
    """Parse unified diffs from LLM output, extracting hunks from fenced blocks."""
    if not content.endswith("\n"):
        content = content + "\n"

    lines = content.splitlines(keepends=True)
    line_num = 0
    edits: list[tuple[str | None, list[str]]] = []
    while line_num < len(lines):
        while line_num < len(lines):
            line = lines[line_num]
            if line.startswith("```diff"):
                line_num, these_edits = process_fenced_block(lines, line_num + 1)
                edits += these_edits
                break
            line_num += 1

    return edits


def process_fenced_block(
    lines: list[str], start_line_num: int
) -> tuple[int, list[tuple[str | None, list[str]]]]:
    """Extract hunks from a fenced diff block."""
    line_num = start_line_num
    for line_num in range(start_line_num, len(lines)):
        line = lines[line_num]
        if line.startswith("```"):
            break

    block = lines[start_line_num:line_num]
    block.append("@@ @@")

    if block[0].startswith("--- ") and block[1].startswith("+++ "):
        a_fname = block[0][4:].strip()
        b_fname = block[1][4:].strip()

        if (a_fname.startswith("a/") or a_fname == "/dev/null") and b_fname.startswith("b/"):
            fname: str | None = b_fname[2:]
        else:
            fname = b_fname

        block = block[2:]
    else:
        fname = None

    edits: list[tuple[str | None, list[str]]] = []

    keeper = False
    hunk: list[str] = []
    op = " "
    for line in block:
        hunk.append(line)
        if len(line) < 2:
            continue

        if line.startswith("+++ ") and hunk[-2].startswith("--- "):
            hunk = hunk[:-3] if hunk[-3] == "\n" else hunk[:-2]
            edits.append((fname, hunk))
            hunk = []
            keeper = False

            fname = line[4:].strip()
            continue

        op = line[0]
        if op in "-+":
            keeper = True
            continue
        if op != "@":
            continue
        if not keeper:
            hunk = []
            continue

        hunk = hunk[:-1]
        edits.append((fname, hunk))
        hunk = []
        keeper = False

    return line_num + 1, edits


def hunk_to_before_after(hunk: list[str]) -> tuple[str, str]:
    """Convert a hunk to before and after text representations.

    In unified diff format, lines follow this structure:
    - Context line: ' content' (space + content)
    - Removed line: '- content' (dash + space + content)
    - Added line: '+ content' (plus + space + content)

    The space after the operator is formatting, not part of the actual line.
    We strip it to get the actual content.

    Handles malformed diffs where LLMs:
    - Omit the operator for context lines
    - Double the operator (e.g., '--line' instead of '- line' when they think line starts with -)
    """
    before: list[str] = []
    after: list[str] = []
    for line in hunk:
        if len(line) < 2:
            op = " "
            content = line
        else:
            op = line[0]
            rest = line[1:]

            # Handle malformed diffs where LLM doubles operators
            # Pattern: '--' or '+-' at line start when LLM thinks content starts with that char
            # But in markdown docs, prose lines don't start with - unless they're list items
            # If we see '--' or '+-', check if this looks like the LLM incorrectly doubling
            if len(rest) > 0 and rest[0] in "-+" and op in "-+":
                # Could be doubled operator or could be legitimate (removing/adding a line that starts with -/+)
                # Heuristic: if the next char after the potential double is a letter or space,
                # it's likely a malformed double that should be stripped
                if len(rest) > 1 and (rest[1].isalpha() or rest[1].isupper() or rest[1] == " "):
                    # This looks like malformed doubling - skip the second operator
                    content = rest[1:]
                else:
                    # Might be legitimate - keep the second operator as content
                    content = rest
            elif rest and rest[0] == " ":
                # Normal case: operator followed by space
                content = rest[1:]
            else:
                content = rest

        if op == " ":
            before.append(content)
            after.append(content)
        elif op == "-":
            before.append(content)
        elif op == "+":
            after.append(content)
        else:
            # Malformed diff: line with no operator
            # Treat it as a context line (present in both before and after)
            # The full line including the invalid operator becomes the content
            full_line = op + content
            before.append(full_line)
            after.append(full_line)

    # Clean prompt artifacts from the result
    return clean_search_replace_block("".join(before), "".join(after))


def search_and_replace(before: str, after: str, content: str) -> str | None:
    """Simple string replacement - returns None if before not found or not unique."""
    num = content.count(before)
    if num == 0:
        return None
    if num > 1:
        # Only refuse if there's very little context
        before_lines = "".join([line.strip() for line in before.splitlines(keepends=True)])
        if len(before_lines) < 10:
            return None

    return content.replace(before, after)


def directly_apply_hunk(content: str, hunk: list[str]) -> str | None:
    """Try to apply hunk via direct string replacement."""
    before, after = hunk_to_before_after(hunk)

    if not before:
        return None

    return search_and_replace(before, after, content)


def apply_partial_hunk(
    content: str,
    preceding_context: list[str],
    changes: list[str],
    following_context: list[str],
) -> str | None:
    """Try applying hunk with progressively less context until it works."""
    len_prec = len(preceding_context)
    len_foll = len(following_context)

    use_all = len_prec + len_foll

    for drop in range(use_all + 1):
        use = use_all - drop

        for use_prec in range(len_prec, -1, -1):
            if use_prec > use:
                continue

            use_foll = use - use_prec
            if use_foll > len_foll:
                continue

            this_prec = preceding_context[-use_prec:] if use_prec else []
            this_foll = following_context[:use_foll]

            res = directly_apply_hunk(content, this_prec + changes + this_foll)
            if res:
                return res

    return None


def apply_hunk(content: str, hunk: list[str]) -> str | None:
    """Apply a hunk with fallback strategies."""
    # Try direct application first
    res = directly_apply_hunk(content, hunk)
    if res:
        return res

    # If direct fails, split into sections and try with progressively less context
    ops = "".join([line[0] if len(line) >= 1 else " " for line in hunk])
    ops = ops.replace("-", "x")
    ops = ops.replace("+", "x")
    ops = ops.replace("\n", " ")

    cur_op = " "
    section: list[str] = []
    sections: list[list[str]] = []

    for i in range(len(ops)):
        op = ops[i]
        if op != cur_op:
            sections.append(section)
            section = []
            cur_op = op
        section.append(hunk[i])

    sections.append(section)
    if cur_op != " ":
        sections.append([])

    all_done = True
    for i in range(2, len(sections), 2):
        preceding_context: list[str] = sections[i - 2]
        changes: list[str] = sections[i - 1]
        following_context: list[str] = sections[i]

        res = apply_partial_hunk(content, preceding_context, changes, following_context)
        if res:
            content = res
        else:
            all_done = False
            break

    if all_done:
        return content

    return None


def try_markdown_bullet_fallback(content: str, before_text: str, after_text: str) -> str | None:
    """Handle case where LLM strips markdown bullets from the diff.

    Example:
        Original: "- Item 1\n- Item 2\n"
        LLM before: "Item 1\nItem 2\n" (missing bullets)

    Tries to find the content by adding "- " prefix to each line.
    """
    # Skip if text is too short
    if len(before_text.strip()) < 20:
        return None

    # Skip if no newlines (single line)
    if "\n\n" in before_text.strip() or "\n" not in before_text:
        return None

    # Try adding "- " to the start of each line
    before_lines = before_text.rstrip("\n").split("\n")
    before_with_bullets = "\n".join("- " + line for line in before_lines) + "\n"

    if before_with_bullets not in content:
        return None

    # Found it! Now build the replacement with bullets
    after_lines = after_text.rstrip("\n").split("\n")
    after_with_bullets = "\n".join("- " + line for line in after_lines) + "\n"

    return content.replace(before_with_bullets, after_with_bullets, 1)


def try_split_line_fallback(content: str, before_text: str, after_text: str) -> str | None:
    """Handle case where LLM splits a single line into multiple lines.

    Example:
        Original: "sentence1. sentence2.\n"
        LLM before: "sentence1.\nsentence2.\n"
        LLM after: "new1.\nnew2.\n\npara2.\n"

    Finds the original by joining before_text lines with spaces,
    then replaces with after_text preserving its original structure.
    """
    # Only try if before_text has single newlines (not paragraph breaks)
    if "\n\n" in before_text.strip() or "\n" not in before_text:
        return None

    # Skip if the text is too short (ambiguous matches)
    if len(before_text.strip()) < 30:
        return None

    # Try replacing each newline in before_text with a space
    # and see if that exists in content
    before_lines = before_text.rstrip("\n").split("\n")

    # Join with space instead of newline
    before_joined = " ".join(line.strip() for line in before_lines if line.strip())

    # Check if this exists in content (as one line)
    if before_joined not in content:
        return None

    # Found it! Replace with after_text as-is (preserving its line structure)
    # But we need to handle the case where after_text might also need to be joined
    # Actually no - we should preserve after_text structure
    # The after text represents the NEW desired structure
    return content.replace(before_joined, after_text.rstrip("\n"), 1)


def normalize_markdown_output(content: str) -> str:
    """Post-process output to fix common LLM diff application issues.

    Fixes critical issues:
    1. Double list markers (e.g., "- - Item" -> "- Item")
    2. Duplicate consecutive identical lines
    3. List markers before headings (e.g., "- ### Heading")
    4. Missing list bullets on bolded items
    5. Missing blank lines before headings
    6. Indented sub-items that should be plain list items
    """
    lines = content.split("\n")
    result: list[str] = []

    for i, line in enumerate(lines):
        # Skip duplicate consecutive lines
        if i > 0 and line == lines[i - 1]:
            continue

        # Fix double list markers: "- - Item" -> "- Item"
        if line.startswith("- - "):
            result.append("- " + line[4:])
            continue

        # Fix indented sub-items that should be regular list items
        # Pattern: "  - Severity:" -> "- Severity:"
        if line.startswith("  - ") or line.startswith("   - "):
            stripped = line.lstrip()
            if stripped.startswith("- "):
                result.append(stripped)
                continue

        # Fix malformed nested bullets (e.g., "-  - item" should be "  - item")
        if line.startswith("-  -"):
            result.append("  " + line[4:])
            continue

        # Fix list markers before headings
        if line.startswith("- #"):
            result.append(line[2:])
            continue

        # Fix missing list bullets on bolded items within list context
        # Pattern: "**Item**:" without leading "- " when in list
        if line.startswith("**") and "**:" in line and result:
            prev = result[-1] if result else ""
            # If previous line was a list item, this should be too
            if prev.startswith("- "):
                result.append("- " + line)
                continue

        # Add blank line before headings if missing
        if line.startswith("#") and result and result[-1] != "":
            result.append("")

        result.append(line)

    # Second pass: remove duplicate section headers
    final_result: list[str] = []
    seen_headers: set[str] = set()

    for line in result:
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped in seen_headers:
                # Skip duplicate header - also skip any blank line before it
                if final_result and final_result[-1] == "":
                    final_result.pop()
                continue
            seen_headers.add(stripped)
        final_result.append(line)

    return "\n".join(final_result)


def find_insertion_point(content: str, _hunk: list[str], after_text: str) -> tuple[str, str] | None:
    """Find where to insert pure-addition hunks by looking at document structure.

    When a hunk has only + lines (no - or context), we need to figure out where
    it should go. We insert ### subsections right before the next ## section.

    Returns (before_part, after_part) if found, None otherwise.
    """
    content_lines = content.splitlines(keepends=True)
    after_lines = after_text.rstrip("\n").split("\n")

    if not after_lines:
        return None

    first_line = after_lines[0].strip()

    # If inserting a ### subsection, place it before the next ## section
    if first_line.startswith("###"):
        # Find the FIRST ## section that appears in content
        # We want to insert before it (so the ### stays in the previous section)
        for i, line in enumerate(content_lines):
            line_str = line.rstrip("\n")
            if line_str.startswith("## ") and not line_str.startswith("### "):
                # Found a ## section - insert before it
                before_part = "".join(content_lines[:i])
                after_part = "".join(content_lines[i:])

                # Ensure proper spacing
                if not before_part.endswith("\n\n"):
                    if not before_part.endswith("\n"):
                        before_part += "\n"
                    before_part += "\n"

                return (before_part, after_part)

        # No ## section found - this is unexpected, but append to end
        return None

    return None


def do_replace(content: str, hunk: list[str]) -> str | None:
    """Apply a single hunk to content, with all fallback strategies."""
    before_text, after_text = hunk_to_before_after(hunk)

    # Handle pure insertions (no before text) - try to find where to insert
    if not before_text.strip():
        result = find_insertion_point(content, hunk, after_text)
        if result:
            before_part, after_part = result
            return before_part + after_text + after_part
        return content + after_text

    # Try strategies in order until one works
    for strategy in [
        lambda: apply_hunk(content, hunk),
        lambda: replace_most_similar_chunk(content, before_text, after_text),
        lambda: try_markdown_bullet_fallback(content, before_text, after_text),
        lambda: try_split_line_fallback(content, before_text, after_text),
    ]:
        result = strategy()
        if result:
            return result

    return None


@register_algorithm
class AiderUdiffAlgorithm(Algorithm):
    """Aider's unified diff with context-based matching and fallback strategies."""

    name = "aider_udiff"
    description = "Aider's udiff using context-based matching (ignores line numbers)"
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
        edits = find_diffs(diff_content)

        if not edits:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No diffs found in LLM output",
                usage=usage,
            )

        # Apply all hunks (we expect single file editing for markdown)
        content = initial
        warnings: list[str] = []
        for i, (_path, hunk) in enumerate(edits, 1):
            result = do_replace(content, hunk)
            if result is None:
                warnings.append(f"Hunk {i}: could not find matching context")
            else:
                content = result

        # Post-process to fix common issues from malformed diffs
        content = normalize_markdown_output(content)

        return AlgorithmResult(
            output=content,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

"""Aider's unified diff algorithm - context-based matching with fallback strategies."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import (
    clean_search_replace_block,
    replace_most_similar_chunk,
)
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """Act as an expert software developer.
Always use best practices when coding.
Respect and use existing conventions, libraries, etc that are already present in the code base.

Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

For each file that needs to be changed, write out the changes similar to a unified diff like `diff -U0` would produce.

# File editing rules:

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

USER_PROMPT = """Here is the current document:

<original_document>
{initial}
</original_document>

Please make these changes:

<requested_changes>
{changes}
</requested_changes>

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
    """Convert a hunk to before and after text representations."""
    before: list[str] = []
    after: list[str] = []
    for line in hunk:
        if len(line) < 2:
            op = " "
            content = line
        else:
            op = line[0]
            content = line[1:]

        if op == " ":
            before.append(content)
            after.append(content)
        elif op == "-":
            before.append(content)
        elif op == "+":
            after.append(content)

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


def do_replace(content: str, hunk: list[str]) -> str | None:
    """Apply a single hunk to content, with all fallback strategies."""
    before_text, after_text = hunk_to_before_after(hunk)

    # Handle appending to file (no before text)
    if not before_text.strip():
        return content + after_text

    # Try direct hunk application first
    result = apply_hunk(content, hunk)
    if result:
        return result

    # Fall back to fuzzy matching from aider_utils
    return replace_most_similar_chunk(content, before_text, after_text)


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
        try:
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
            for _path, hunk in edits:
                result = do_replace(content, hunk)
                if result is None:
                    before_text, _ = hunk_to_before_after(hunk)
                    return AlgorithmResult(
                        output=None,
                        success=False,
                        error=f"Hunk failed to apply - could not find matching context:\n{before_text[:200]}",
                        usage=usage,
                    )
                content = result

            return AlgorithmResult(
                output=content,
                success=True,
                error=None,
                usage=usage,
            )
        except Exception as e:
            return AlgorithmResult(
                output=None,
                success=False,
                error=f"Failed to apply diff: {e}",
                usage=usage,
            )

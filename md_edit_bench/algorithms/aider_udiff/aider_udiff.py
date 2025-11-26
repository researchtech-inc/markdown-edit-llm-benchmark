"""Aider's unified diff algorithm - context-based matching with fallback strategies."""

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


def format_failed_hunks(failed: list[tuple[int, list[str]]]) -> str:
    """Format failed hunks for the retry prompt."""
    parts: list[str] = []
    for hunk_num, hunk in failed:
        before, after = hunk_to_before_after(hunk)
        parts.append(f"Hunk {hunk_num}:")
        parts.append(f"BEFORE:\n{before}")
        parts.append(f"AFTER:\n{after}")
        parts.append("")
    return "\n".join(parts)


class AiderUdiffAlgorithm(Algorithm):
    """Aider's unified diff with context-based matching and fallback strategies."""

    name = "aider_udiff"
    description = "Aider's udiff using context-based matching (ignores line numbers)"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Generate diff
        diff_content, usage = await call_llm(model, user_prompt, system_prompt)

        # Parse and apply diffs
        edits = find_diffs(diff_content)

        if not edits:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No diffs found in LLM output",
                usage=usage,
            )

        # Apply all hunks, collect failures
        content = initial
        failed_hunks: list[tuple[int, list[str]]] = []
        for i, (_path, hunk) in enumerate(edits, 1):
            result = do_replace(content, hunk)
            if result is None:
                failed_hunks.append((i, hunk))
            else:
                content = result

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

        retry_edits = find_diffs(retry_output)

        # Track which original hunks remain unrecovered
        warnings: list[str] = []

        if not retry_edits:
            # Retry produced no hunks - all original failures become warnings
            for hunk_num, _hunk in failed_hunks:
                warnings.append(f"Hunk {hunk_num}: failed and retry produced no fix")
        else:
            # Apply retry hunks, track failures
            retry_failed_count = 0
            for _i, (_path, hunk) in enumerate(retry_edits, 1):
                new_result = do_replace(content, hunk)
                if new_result is None:
                    retry_failed_count += 1
                else:
                    content = new_result

            # If retry returned fewer hunks than failures, or some retry hunks failed,
            # report the unrecovered count as warnings
            unrecovered = len(failed_hunks) - (len(retry_edits) - retry_failed_count)
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

"""Aider diff-fenced v2 - double pass with LLM retry for failed blocks."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_diff_fenced import (
    FORMAT_SPECIFICATION,
    SYSTEM_PROMPT,
    parse_diff_fenced_blocks,
)
from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

USER_PROMPT = f"""Edit the following document according to the requested changes.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

CRITICAL - THE MATCHING ALGORITHM WORKS LINE-BY-LINE:
When you create a SEARCH block, the system will try to find those exact lines in the document.
It compares line-by-line. A partial line match will FAIL.

Before writing any SEARCH block:
1. Locate the target text in the original document above
2. Check if there's MORE TEXT on that same line (before the newline character)
3. If yes, include ALL text from that line in your SEARCH

EXAMPLE OF WHAT WILL FAIL:
Original document line: "Sales grew 15%. We expanded globally."
Your SEARCH: "We expanded globally."  ← FAILS! This is only part of the line.
Correct SEARCH: "Sales grew 15%. We expanded globally."  ← SUCCESS! Complete line.

{FORMAT_SPECIFICATION}

Output the *SEARCH/REPLACE blocks* in diff-fenced format:"""

RETRY_PROMPT = f"""The following SEARCH/REPLACE blocks failed to match the current document state.
The document has been partially modified by earlier blocks. Please provide corrected blocks
that will match the CURRENT document state shown below.

<current_document>
{{current}}
</current_document>

<failed_blocks>
{{failed_blocks}}
</failed_blocks>

For each failed block, output a corrected SEARCH/REPLACE block where the SEARCH text
matches the CURRENT document (not the original). The REPLACE text should achieve the
same intended change.

CRITICAL: The SEARCH section must EXACTLY match the document's line structure:
- If multiple sentences are on the same line in the document, keep them together in SEARCH
- Preserve the exact paragraph breaks and line structure from the document
- Do not add or remove line breaks compared to the original structure

{FORMAT_SPECIFICATION}

Output only the corrected *SEARCH/REPLACE blocks* in diff-fenced format:"""


class DiffFencedV2Error(Exception):
    """Raised when diff-fenced blocks cannot be parsed or applied."""


def format_failed_blocks(failed: list[tuple[int, str, str]]) -> str:
    """Format failed blocks for the retry prompt."""
    parts: list[str] = []
    for block_num, search, replace in failed:
        parts.append(f"Block {block_num}:")
        parts.append(f"SEARCH:\n{search}")
        parts.append(f"REPLACE:\n{replace}")
        parts.append("")
    return "\n".join(parts)


@register_algorithm
class AiderDiffFencedV2Algorithm(Algorithm):
    """Aider diff-fenced v2 - double pass with LLM retry for failed blocks."""

    name = "aider_diff_fenced_v2"
    description = "Aider diff-fenced with LLM retry for failed blocks"
    accepts_model = True
    default_model = "openai/gpt-4.1"

    async def apply(
        self,
        initial: str,
        changes: str,
        model: str | None = None,
    ) -> AlgorithmResult:
        model = model or self.default_model
        assert model is not None

        # Pass 1: Initial LLM call
        user_prompt = USER_PROMPT.format(initial=initial, changes=changes)
        llm_output, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        blocks = parse_diff_fenced_blocks(llm_output)
        if not blocks:
            return AlgorithmResult(
                output=None,
                success=False,
                error="No valid SEARCH/REPLACE blocks found",
                usage=usage,
            )

        # Apply blocks, collect failures
        result = initial
        failed_blocks: list[tuple[int, str, str]] = []

        for i, (search, replace) in enumerate(blocks, 1):
            new_result = replace_most_similar_chunk(result, search, replace)
            if new_result is None:
                failed_blocks.append((i, search, replace))
            else:
                result = new_result

        if not failed_blocks:
            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
            )

        # Pass 2: Retry failed blocks with LLM
        retry_prompt = RETRY_PROMPT.format(
            current=result,
            failed_blocks=format_failed_blocks(failed_blocks),
        )
        retry_output, retry_usage = await call_llm(model, retry_prompt, SYSTEM_PROMPT)
        usage = usage + retry_usage

        retry_blocks = parse_diff_fenced_blocks(retry_output)

        # Track which original blocks remain unrecovered
        warnings: list[str] = []

        if not retry_blocks:
            # Retry produced no blocks - all original failures become warnings
            for block_num, _search, _replace in failed_blocks:
                warnings.append(f"Block {block_num}: failed and retry produced no fix")
        else:
            # Apply retry blocks, track failures
            retry_failed_count = 0
            for _i, (search, replace) in enumerate(retry_blocks, 1):
                new_result = replace_most_similar_chunk(result, search, replace)
                if new_result is None:
                    retry_failed_count += 1
                else:
                    result = new_result

            # If retry returned fewer blocks than failures, or some retry blocks failed,
            # report the unrecovered count as warnings
            unrecovered = len(failed_blocks) - (len(retry_blocks) - retry_failed_count)
            if unrecovered > 0:
                warnings.append(
                    f"{unrecovered} block(s) unrecovered after retry "
                    f"(original failures: {[b[0] for b in failed_blocks]})"
                )

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=warnings,
        )

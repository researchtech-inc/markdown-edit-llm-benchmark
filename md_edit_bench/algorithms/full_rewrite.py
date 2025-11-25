"""Full rewrite algorithm - LLM outputs the entire edited document."""

from __future__ import annotations

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

SYSTEM_PROMPT = """You are an expert document editor. Given a document and requested changes, generate the COMPLETE edited document with all changes applied.

## CRITICAL RULES
1. Output the COMPLETE document with all changes applied
2. Preserve the overall structure and formatting of the original
3. Apply all requested changes accurately
4. Do not add explanations or commentary - just output the edited document
5. Include ALL original content that should be kept, plus the new/modified content
6. NEVER skip, omit, or elide content using "..." or comments like "rest of content unchanged"
7. NEVER use placeholders or abbreviations - output the full document

Output ONLY the edited document, nothing else."""

USER_PROMPT = """Apply the following changes to the document and return the complete edited document.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>

Output the complete edited document:"""


@register_algorithm
class FullRewriteAlgorithm(Algorithm):
    """LLM outputs the entire edited document (simple but potentially expensive)."""

    name = "full_rewrite"
    description = "LLM outputs complete edited document (simple, higher token cost)"
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

        result, usage = await call_llm(model, user_prompt, SYSTEM_PROMPT)

        # Clean up result if wrapped in code blocks
        result_clean = result.strip()
        if result_clean.startswith("```"):
            first_newline = result_clean.find("\n")
            if first_newline != -1:
                result_clean = result_clean[first_newline + 1 :]
            if result_clean.endswith("```"):
                result_clean = result_clean[:-3].rstrip()

        return AlgorithmResult(
            output=result_clean,
            success=True,
            error=None,
            usage=usage,
        )

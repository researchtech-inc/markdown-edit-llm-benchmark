"""Full rewrite algorithm - LLM outputs the entire edited document."""

from __future__ import annotations

from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class FullRewriteAlgorithm(Algorithm):
    """LLM outputs the entire edited document (simple but potentially expensive)."""

    name = "full_rewrite"
    description = "LLM outputs complete edited document (simple, higher token cost)"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        result, usage = await call_llm(model, user_prompt, system_prompt)

        # Clean up result if wrapped in code blocks
        result_clean = result.strip()

        # Remove XML tags
        if result_clean.startswith("<document>"):
            result_clean = result_clean.split("<document>", 1)[1]
        result_clean = result_clean.split("</document>", 1)[0]

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

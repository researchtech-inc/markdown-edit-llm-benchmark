"""Morph algorithm - Generator + Morph merger pipeline with explicit edit hints."""

from __future__ import annotations

from md_edit_bench import config
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


def _strip_code_blocks(text: str) -> str:
    """Remove markdown code block wrapper if present."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3].rstrip()
    return text


class MorphAlgorithm(Algorithm):
    """Two-step: Generator LLM creates draft, Morph merges into original."""

    name = "morph"
    description = "Generator LLM + Morph merger pipeline"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        # Step 1: Generator - LLM creates edit instructions (not full document)
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)
        draft, usage_generator = await call_llm(model, user_prompt, system_prompt)
        draft_clean = _strip_code_blocks(draft)

        # Step 2: Morph - merge draft into original
        morph_prompt = (
            f"<instruction>Apply the update to the code.</instruction>\n"
            f"<code>{initial}</code>\n"
            f"<update>{draft_clean}</update>"
        )
        result, usage_morph = await call_llm(config.MORPH_MODEL, morph_prompt)
        result_clean = _strip_code_blocks(result)

        # Combine usage from both calls
        total_usage = usage_generator + usage_morph

        return AlgorithmResult(
            output=result_clean,
            success=True,
            error=None,
            usage=total_usage,
        )

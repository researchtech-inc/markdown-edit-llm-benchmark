"""Morph algorithm - Generator + Morph merger pipeline."""

from __future__ import annotations

from md_edit_bench import config
from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

GENERATOR_SYSTEM_PROMPT = """You are an expert coding assistant.
Your task is to generate the code for the requested changes.

## CRITICAL PERFORMANCE RULES
1. **DO NOT** output the entire file.
2. Output **ONLY** the specific functions, blocks, or paragraphs that need to change.
3. Include 2-3 lines of context (unchanged code) around your changes to help locate them.
4. If there are multiple separate changes, separate them with `...` or a newline.
"""

GENERATOR_USER_PROMPT = """Apply the following changes to the document.

<original>
{initial}
</original>

<changes>
{changes}
</changes>

Output the complete edited document:"""


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


@register_algorithm
class MorphAlgorithm(Algorithm):
    """Two-step: Generator LLM creates draft, Morph merges into original."""

    name = "morph"
    description = "Generator LLM + Morph merger pipeline"
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

        # Step 1: Generator - LLM creates edited document
        user_prompt = GENERATOR_USER_PROMPT.format(initial=initial, changes=changes)
        draft, usage_generator = await call_llm(model, user_prompt, GENERATOR_SYSTEM_PROMPT)
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

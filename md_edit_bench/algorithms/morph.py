"""Morph algorithm - Generator + Morph merger pipeline with explicit edit hints."""

from __future__ import annotations

from md_edit_bench import config
from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult

FORMAT_SPECIFICATION = """Output ONLY the edited regions, not the whole document.

FORMAT:
- // prefix = unchanged line from original (context/anchor)
- No prefix = NEW or CHANGED content (the actual edit)
- // alone = blank line from original

CRITICAL: Your output MUST contain lines WITHOUT // prefix - those are the actual changes!

EXAMPLE - Adding text:

Original document:
## Section A

Old content here.

## Section B

Edit: Add "New line." after "Old content here."

Correct output:
// Old content here.

New line.

// ## Section B

EXAMPLE - Replacing text:

Original document:
## Results

Bad number.

## End

Edit: Change "Bad number." to "Good number."

Correct output:
// ## Results
//
Good number.
//
// ## End

EXAMPLE - Deleting text:

Original document:
Keep this.

Delete this.

Keep this too.

Edit: Delete "Delete this."

Correct output:
// Keep this.
//
// Keep this too.

WRONG - Do NOT output the entire document with // on every line. Only output the small regions being edited with a few lines of context."""

GENERATOR_SYSTEM_PROMPT = f"""You are an expert editing assistant. Generate edit instructions in the format expected by the Morph apply model.

{FORMAT_SPECIFICATION}"""

GENERATOR_USER_PROMPT = f"""Generate edit instructions for the following document changes.

<original>
{{initial}}
</original>

<changes>
{{changes}}
</changes>

{FORMAT_SPECIFICATION}

Output the edits now:"""


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

        # Step 1: Generator - LLM creates edit instructions (not full document)
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

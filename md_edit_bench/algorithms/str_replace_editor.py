"""Str Replace Editor algorithm - strict exact-match string replace (OpenHands-style)."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult


class StrReplaceCommand(BaseModel):
    command: Literal["str_replace"]
    old_str: str
    new_str: str


class CommandsList(BaseModel):
    commands: list[StrReplaceCommand]


FORMAT_SPECIFICATION = """## Output Format

Output a JSON object with a "commands" array:

{{
  "commands": [
    {{"command": "str_replace", "old_str": "exact text to find", "new_str": "replacement text"}},
    {{"command": "str_replace", "old_str": "another exact text", "new_str": "another replacement"}}
  ]
}}

## CRITICAL RULES

1. **EXACT MATCHING REQUIRED**: The `old_str` must match EXACTLY in the document - character for character, including all whitespace, indentation, and newlines.

2. **UNIQUENESS CONSTRAINT**: Each `old_str` must appear EXACTLY ONCE in the document. If it appears zero times or multiple times, the command will fail.

3. **Choose unique snippets**: Select text that is specific enough to appear only once. Include surrounding context lines if needed to make the match unique.

4. **For additions**: Include the line(s) before where you want to add content in `old_str`, then include those same lines PLUS the new content in `new_str`.

5. **For deletions**: Include the text to delete in `old_str`, and omit it from `new_str` (keeping surrounding context).

6. **Multiple changes**: Use separate commands for changes in different parts of the document. Commands are applied sequentially."""

SYSTEM_PROMPT = f"""You are an expert document editor. Given a document and requested changes, generate str_replace commands to implement the changes.

{FORMAT_SPECIFICATION}"""

USER_PROMPT = f"""Generate str_replace commands to implement the following changes.

<original_document>
{{initial}}
</original_document>

<requested_changes>
{{changes}}
</requested_changes>

{FORMAT_SPECIFICATION}"""


class StrReplaceError(Exception):
    """Raised when a str_replace command cannot be applied."""


def repair_json(raw_json: str) -> str:
    """Attempt to repair common JSON formatting issues."""
    text = raw_json.strip()

    # Extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    # Remove any leading/trailing non-JSON content
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start : brace_end + 1]

    # Try to fix truncated JSON by closing unclosed strings, arrays, and objects
    if text.count('"') % 2 == 1:
        # Odd number of quotes - likely truncated string
        text = text.rstrip() + '"'

    # Count braces and brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # Close unclosed structures
    text = text.rstrip().rstrip(",")  # Remove trailing commas
    text += "]" * open_brackets
    text += "}" * open_braces

    return text


def parse_commands(raw_json: str) -> CommandsList:
    """Parse CommandsList from JSON with fallback repair logic."""
    # First, try direct parsing
    try:
        return CommandsList.model_validate_json(raw_json)
    except ValidationError:
        pass

    # Try repairing the JSON
    repaired = repair_json(raw_json)
    try:
        return CommandsList.model_validate_json(repaired)
    except ValidationError:
        pass

    # Last resort: parse and validate in two steps
    try:
        return CommandsList.model_validate(json.loads(repaired))
    except (json.JSONDecodeError, ValidationError):
        pass

    raise StrReplaceError(
        f"Failed to parse JSON response after all repair attempts. Raw response: {raw_json[:500]}"
    )


def apply_str_replace(initial: str, commands: list[StrReplaceCommand]) -> tuple[str, list[str]]:
    """Apply str_replace commands with strict exact matching.

    Returns (result, warnings) tuple. Skipped commands are reported as warnings.
    Raises StrReplaceError only if no commands provided.
    """
    if not commands:
        raise StrReplaceError("No commands to apply")

    result = initial
    warnings: list[str] = []
    for i, cmd in enumerate(commands, 1):
        occurrences = result.count(cmd.old_str)
        if occurrences == 0:
            warnings.append(f"Command {i}: old_str not found in document")
            continue
        if occurrences > 1:
            warnings.append(f"Command {i}: old_str found {occurrences} times (ambiguous)")
            continue

        result = result.replace(cmd.old_str, cmd.new_str, 1)

    return result, warnings


@register_algorithm
class StrReplaceEditorAlgorithm(Algorithm):
    """LLM outputs JSON array of str_replace commands with strict exact matching."""

    name = "str_replace_editor"
    description = "Exact-match string replace commands in JSON (OpenHands-style)"
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

        raw_json, usage = await call_llm(
            model, user_prompt, SYSTEM_PROMPT, response_format=CommandsList
        )

        try:
            commands_list = parse_commands(raw_json)
            result, warnings = apply_str_replace(initial, commands_list.commands)
            return AlgorithmResult(
                output=result, success=True, error=None, usage=usage, warnings=warnings
            )
        except StrReplaceError as e:
            return AlgorithmResult(output=None, success=False, error=str(e), usage=usage)

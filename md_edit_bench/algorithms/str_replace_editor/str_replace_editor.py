"""Str Replace Editor algorithm - strict exact-match string replace (OpenHands-style)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class StrReplaceCommand(BaseModel):
    command: Literal["str_replace"]
    old_str: str
    new_str: str


class CommandsList(BaseModel):
    commands: list[StrReplaceCommand]


class StrReplaceError(Exception):
    """Raised when a str_replace command cannot be applied."""


def apply_str_replace(
    initial: str, commands: list[StrReplaceCommand]
) -> tuple[str, list[tuple[int, StrReplaceCommand, str]]]:
    """Apply str_replace commands with strict exact matching.

    Returns (result, failed_commands) tuple where failed_commands contains
    (command_index, command, reason) tuples for commands that couldn't be applied.
    Raises StrReplaceError only if no commands provided.
    """
    if not commands:
        raise StrReplaceError("No commands to apply")

    result = initial
    failed: list[tuple[int, StrReplaceCommand, str]] = []
    for i, cmd in enumerate(commands, 1):
        occurrences = result.count(cmd.old_str)
        if occurrences == 0:
            failed.append((i, cmd, "old_str not found in document"))
            continue
        if occurrences > 1:
            failed.append((i, cmd, f"old_str found {occurrences} times (ambiguous)"))
            continue

        result = result.replace(cmd.old_str, cmd.new_str, 1)

    return result, failed


def format_failed_commands(failed: list[tuple[int, StrReplaceCommand, str]]) -> str:
    """Format failed commands for the retry prompt."""
    parts: list[str] = []
    for cmd_num, cmd, reason in failed:
        parts.append(f"Command {cmd_num} ({reason}):")
        parts.append(f"old_str: {cmd.old_str!r}")
        parts.append(f"new_str: {cmd.new_str!r}")
        parts.append("")
    return "\n".join(parts)


class StrReplaceEditorAlgorithm(Algorithm):
    """LLM outputs JSON array of str_replace commands with strict exact matching."""

    name = "str_replace_editor"
    description = "Exact-match string replace commands in JSON (OpenHands-style)"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        raw_json, usage = await call_llm(
            model, user_prompt, system_prompt, response_format=CommandsList
        )

        try:
            commands_list = CommandsList.model_validate_json(raw_json)
        except StrReplaceError as e:
            return AlgorithmResult(output=None, success=False, error=str(e), usage=usage)
        except Exception as e:
            return AlgorithmResult(
                output=None, success=False, error=f"Parse error: {e}", usage=usage
            )

        # Apply commands, collect failures
        result, failed_commands = apply_str_replace(initial, commands_list.commands)

        if not failed_commands:
            return AlgorithmResult(
                output=result, success=True, error=None, usage=usage, warnings=[]
            )

        # Pass 2: Retry failed commands with LLM
        retry_prompt = pm.get(
            "retry.jinja2",
            current=result,
            failed_commands=format_failed_commands(failed_commands),
        )
        retry_json, retry_usage = await call_llm(
            model, retry_prompt, system_prompt, response_format=CommandsList
        )
        usage = usage + retry_usage

        try:
            retry_commands_list = CommandsList.model_validate_json(retry_json)
        except Exception:
            # Retry parsing failed - convert all original failures to warnings
            warnings = [f"Command {num}: {reason}" for num, _cmd, reason in failed_commands]
            return AlgorithmResult(
                output=result, success=True, error=None, usage=usage, warnings=warnings
            )

        # Apply retry commands
        retry_result, retry_failed = apply_str_replace(result, retry_commands_list.commands)
        result = retry_result

        # Generate warnings for unrecovered failures
        warnings: list[str] = []
        if retry_failed:
            # Some retry commands failed - count these as unrecovered
            warnings.append(
                f"{len(retry_failed)} command(s) failed on retry "
                f"(original failures: {[num for num, _cmd, _reason in failed_commands]})"
            )
        elif len(retry_commands_list.commands) < len(failed_commands):
            # Retry provided fewer commands than failures
            unrecovered = len(failed_commands) - len(retry_commands_list.commands)
            warnings.append(
                f"{unrecovered} command(s) not addressed in retry "
                f"(original failures: {[num for num, _cmd, _reason in failed_commands]})"
            )

        return AlgorithmResult(
            output=result, success=True, error=None, usage=usage, warnings=warnings
        )

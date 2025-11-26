"""JSON operations algorithm - structured replace/insert/delete by section + snippet."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class OperationTarget(BaseModel):
    section: str
    match: str


class ReplaceOperation(BaseModel):
    op: Literal["replace"]
    target: OperationTarget
    replacement: str


class DeleteOperation(BaseModel):
    op: Literal["delete"]
    target: OperationTarget


class InsertAfterOperation(BaseModel):
    op: Literal["insert_after"]
    target: OperationTarget
    content: str


class InsertBeforeOperation(BaseModel):
    op: Literal["insert_before"]
    target: OperationTarget
    content: str


Operation = ReplaceOperation | DeleteOperation | InsertAfterOperation | InsertBeforeOperation


class OperationsList(BaseModel):
    operations: list[Operation]


class JsonOpsError(Exception):
    """Raised when JSON operations cannot be parsed or applied."""


def split_sections(text: str) -> list[tuple[str, int, int, int]]:
    """Split markdown into sections based on headings.

    Returns:
        List of (heading_text, level, start_line, end_line) tuples
    """
    section_re = re.compile(r"^(#+)\s+(.+)$")
    lines = text.splitlines(keepends=True)
    sections: list[tuple[str, int, int, int]] = []

    for i, line in enumerate(lines):
        match = section_re.match(line.rstrip("\n"))
        if match:
            level = len(match.group(1))
            heading_text = match.group(2)
            sections.append((heading_text, level, i, -1))

    for i in range(len(sections)):
        heading_text, level, start, _ = sections[i]

        if i + 1 < len(sections):
            end = sections[i + 1][2]
            for j in range(i + 1, len(sections)):
                if sections[j][1] <= level:
                    end = sections[j][2]
                    break
            else:
                end = len(lines)
        else:
            end = len(lines)

        sections[i] = (heading_text, level, start, end)

    return sections


def get_section_text(doc: str, section_name: str) -> tuple[str, int, int] | None:
    """Get text of a section by heading name.

    Returns:
        Tuple of (section_text, start_char_pos, end_char_pos) or None if not found.
    """
    sections = split_sections(doc)
    lines = doc.splitlines(keepends=True)

    for heading_text, _level, start_line, end_line in sections:
        if heading_text == section_name:
            section_text = "".join(lines[start_line:end_line])
            start_pos = sum(len(lines[i]) for i in range(start_line))
            end_pos = sum(len(lines[i]) for i in range(end_line))
            return section_text, start_pos, end_pos

    return None


def apply_ops(initial: str, ops: list[Operation]) -> tuple[str, list[str], list[Operation]]:
    """Apply JSON operations to document.

    Returns (result, warnings, failed_operations) tuple.
    Skipped operations are reported as warnings and returned in failed_operations.
    Raises JsonOpsError only for unrecoverable errors (no ops, empty section/match).
    """
    if not ops:
        raise JsonOpsError("No operations to apply")

    doc = initial
    warnings: list[str] = []
    failed_ops: list[Operation] = []

    for i, op in enumerate(ops, start=1):
        section_name = op.target.section
        match_text = op.target.match

        if not section_name:
            raise JsonOpsError(f"Operation {i}: target.section is required")
        if not match_text:
            raise JsonOpsError(f"Operation {i}: target.match is required")

        section_result = get_section_text(doc, section_name)
        if section_result is None:
            warnings.append(f"Operation {i}: section '{section_name}' not found")
            failed_ops.append(op)
            continue

        section_text, start_pos, end_pos = section_result

        if isinstance(op, ReplaceOperation):
            new_section = replace_most_similar_chunk(section_text, match_text, op.replacement)
            if new_section is None:
                warnings.append(f"Operation {i}: could not find match in section '{section_name}'")
                failed_ops.append(op)
                continue
            doc = doc[:start_pos] + new_section + doc[end_pos:]

        elif isinstance(op, DeleteOperation):
            new_section = replace_most_similar_chunk(section_text, match_text, "")
            if new_section is None:
                warnings.append(f"Operation {i}: could not find match in section '{section_name}'")
                failed_ops.append(op)
                continue
            doc = doc[:start_pos] + new_section + doc[end_pos:]

        elif isinstance(op, InsertAfterOperation):
            index = section_text.find(match_text)
            if index != -1:
                anchor_end = index + len(match_text)
                new_section = (
                    section_text[:anchor_end] + "\n" + op.content + section_text[anchor_end:]
                )
                doc = doc[:start_pos] + new_section + doc[end_pos:]
            else:
                new_section = replace_most_similar_chunk(
                    section_text, match_text, match_text + "\n" + op.content
                )
                if new_section is None:
                    warnings.append(
                        f"Operation {i}: could not find match in section '{section_name}'"
                    )
                    failed_ops.append(op)
                    continue
                doc = doc[:start_pos] + new_section + doc[end_pos:]

        elif isinstance(op, InsertBeforeOperation):  # pyright: ignore[reportUnnecessaryIsInstance]
            index = section_text.find(match_text)
            if index != -1:
                new_section = section_text[:index] + op.content + "\n" + section_text[index:]
                doc = doc[:start_pos] + new_section + doc[end_pos:]
            else:
                new_section = replace_most_similar_chunk(
                    section_text, match_text, op.content + "\n" + match_text
                )
                if new_section is None:
                    warnings.append(
                        f"Operation {i}: could not find match in section '{section_name}'"
                    )
                    failed_ops.append(op)
                    continue
                doc = doc[:start_pos] + new_section + doc[end_pos:]

    return doc, warnings, failed_ops


def format_failed_operations(failed: list[Operation]) -> str:
    """Format failed operations for the retry prompt."""
    parts: list[str] = []
    for i, op in enumerate(failed, start=1):
        parts.append(f"Operation {i}:")
        parts.append(f"  op: {op.op}")
        parts.append(f"  section: {op.target.section}")
        parts.append(f"  match: {op.target.match}")
        if isinstance(op, ReplaceOperation):
            parts.append(f"  replacement: {op.replacement}")
        elif isinstance(op, InsertAfterOperation | InsertBeforeOperation):
            parts.append(f"  content: {op.content}")
        parts.append("")
    return "\n".join(parts)


class JsonOpsAlgorithm(Algorithm):
    """Structured JSON operations (replace/insert/delete by section + snippet)."""

    name = "json_ops"
    description = "Structured JSON operations (replace/insert/delete by section + snippet)"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        raw_json, usage = await call_llm(
            model, user_prompt, system_prompt, response_format=OperationsList
        )

        try:
            ops_list = OperationsList.model_validate_json(raw_json)
            result, warnings, failed_ops = apply_ops(initial, ops_list.operations)

            # If no failures, return immediately
            if not failed_ops:
                return AlgorithmResult(
                    output=result, success=True, error=None, usage=usage, warnings=warnings
                )

            # Pass 2: Retry failed operations with LLM
            retry_prompt = pm.get(
                "retry.jinja2",
                current=result,
                failed_operations=format_failed_operations(failed_ops),
            )
            retry_json, retry_usage = await call_llm(
                model, retry_prompt, system_prompt, response_format=OperationsList
            )
            usage = usage + retry_usage

            retry_ops_list = OperationsList.model_validate_json(retry_json)

            # Track which operations remain unrecovered
            retry_warnings: list[str] = []

            if not retry_ops_list.operations:
                # Retry produced no operations - all original failures become warnings
                retry_warnings.append(
                    f"{len(failed_ops)} operation(s) failed and retry produced no fix"
                )
            else:
                # Apply retry operations, track failures
                result, _retry_apply_warnings, retry_failed_ops = apply_ops(
                    result, retry_ops_list.operations
                )

                # If retry operations failed, report the unrecovered count
                unrecovered = len(failed_ops) - (
                    len(retry_ops_list.operations) - len(retry_failed_ops)
                )
                if unrecovered > 0:
                    retry_warnings.append(f"{unrecovered} operation(s) unrecovered after retry")

            return AlgorithmResult(
                output=result,
                success=True,
                error=None,
                usage=usage,
                warnings=warnings + retry_warnings,
            )

        except JsonOpsError as e:
            return AlgorithmResult(output=None, success=False, error=str(e), usage=usage)
        except Exception as e:
            return AlgorithmResult(
                output=None, success=False, error=f"Parse error: {e}", usage=usage
            )

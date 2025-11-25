"""JSON operations algorithm - structured replace/insert/delete by section + snippet."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.algorithms.aider_utils import replace_most_similar_chunk
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult


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


SYSTEM_PROMPT = """You are an expert document editor. Given a document and requested changes, generate structured operations.

## JSON Schema

Output a JSON object with an "operations" array:

{
  "operations": [
    {
      "op": "replace",
      "target": {"section": "Executive Summary", "match": "exact snippet"},
      "replacement": "new text"
    },
    {
      "op": "insert_after",
      "target": {"section": "Key Highlights", "match": "anchor text"},
      "content": "new content to insert"
    },
    {
      "op": "insert_before",
      "target": {"section": "Introduction", "match": "anchor text"},
      "content": "new content to insert"
    },
    {
      "op": "delete",
      "target": {"section": "Conclusion", "match": "text to delete"}
    }
  ]
}

## Supported Operations

- `replace`: Replace matched text with replacement text
- `insert_after`: Insert content after the matched anchor text
- `insert_before`: Insert content before the matched anchor text
- `delete`: Delete the matched text

## CRITICAL RULES

1. **Section names**: `target.section` must match an existing heading title exactly (without the # symbols)
2. **Match text**: `target.match` should be a snippet copied verbatim from the original document
3. **Unique matches**: Choose match text that appears only once in the target section
4. **Operations only**: Use only the four allowed operation types: replace, insert_after, insert_before, delete"""

USER_PROMPT = """Generate JSON operations to implement the following changes.

<original_document>
{initial}
</original_document>

<requested_changes>
{changes}
</requested_changes>"""


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


def get_section_text(doc: str, section_name: str) -> tuple[str, int, int]:
    """Get text of a section by heading name.

    Returns:
        Tuple of (section_text, start_char_pos, end_char_pos)
    """
    sections = split_sections(doc)
    lines = doc.splitlines(keepends=True)

    for heading_text, _level, start_line, end_line in sections:
        if heading_text == section_name:
            section_text = "".join(lines[start_line:end_line])
            start_pos = sum(len(lines[i]) for i in range(start_line))
            end_pos = sum(len(lines[i]) for i in range(end_line))
            return section_text, start_pos, end_pos

    raise JsonOpsError(f"Section '{section_name}' not found")


def apply_ops(initial: str, ops: list[Operation]) -> str:
    """Apply JSON operations to document."""
    if not ops:
        raise JsonOpsError("No operations to apply")

    doc = initial

    for i, op in enumerate(ops, start=1):
        section_name = op.target.section
        match_text = op.target.match

        if not section_name:
            raise JsonOpsError(f"Operation {i}: target.section is required")
        if not match_text:
            raise JsonOpsError(f"Operation {i}: target.match is required")

        try:
            section_text, start_pos, end_pos = get_section_text(doc, section_name)
        except JsonOpsError as e:
            raise JsonOpsError(f"Operation {i}: {e}") from e

        if isinstance(op, ReplaceOperation):
            new_section = replace_most_similar_chunk(section_text, match_text, op.replacement)
            if new_section is None:
                raise JsonOpsError(
                    f"Operation {i}: could not find match in section '{section_name}'"
                )
            doc = doc[:start_pos] + new_section + doc[end_pos:]

        elif isinstance(op, DeleteOperation):
            new_section = replace_most_similar_chunk(section_text, match_text, "")
            if new_section is None:
                raise JsonOpsError(
                    f"Operation {i}: could not find match in section '{section_name}'"
                )
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
                    raise JsonOpsError(
                        f"Operation {i}: could not find match in section '{section_name}'"
                    )
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
                    raise JsonOpsError(
                        f"Operation {i}: could not find match in section '{section_name}'"
                    )
                doc = doc[:start_pos] + new_section + doc[end_pos:]

    return doc


@register_algorithm
class JsonOpsAlgorithm(Algorithm):
    """Structured JSON operations (replace/insert/delete by section + snippet)."""

    name = "json_ops"
    description = "Structured JSON operations (replace/insert/delete by section + snippet)"
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
            model, user_prompt, SYSTEM_PROMPT, response_format=OperationsList
        )

        try:
            ops_list = OperationsList.model_validate_json(raw_json)
            result = apply_ops(initial, ops_list.operations)
            return AlgorithmResult(output=result, success=True, error=None, usage=usage)
        except JsonOpsError as e:
            return AlgorithmResult(output=None, success=False, error=str(e), usage=usage)
        except Exception as e:
            return AlgorithmResult(
                output=None, success=False, error=f"Parse error: {e}", usage=usage
            )

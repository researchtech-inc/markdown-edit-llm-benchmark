"""Section rewrite algorithm - LLM outputs only modified sections by heading."""

from __future__ import annotations

import re

from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)


class SectionRewriteError(Exception):
    """Raised when section rewrite cannot be applied."""


def split_sections(text: str) -> list[tuple[str, int, int, int]]:
    """Split markdown into sections based on headings.

    Returns list of (heading_line, level, start_idx, end_idx) tuples.
    Each section includes the heading and all content until next heading of same or higher level.
    """
    lines = text.split("\n")
    sections: list[tuple[str, int, int, int]] = []

    for i, line in enumerate(lines):
        heading_match = re.match(r"^(#+)\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Find end of this section
            end_idx = len(lines)
            for j in range(i + 1, len(lines)):
                next_heading_match = re.match(r"^(#+)\s+", lines[j])
                if next_heading_match:
                    next_level = len(next_heading_match.group(1))
                    if next_level <= level:
                        end_idx = j
                        break

            sections.append((heading_text, level, i, end_idx))

    return sections


def parse_section_blocks(output: str) -> list[tuple[str, str]]:
    """Parse LLM output into (section_name, replacement_text) pairs.

    Extracts sections wrapped in ### SECTION: ... ### END SECTION blocks.
    """
    pattern = r"### SECTION:\s*(.+?)\n(.*?)\n### END SECTION"
    matches: list[tuple[str, str]] = re.findall(pattern, output, re.DOTALL)

    if not matches:
        raise SectionRewriteError("No valid SECTION blocks found in output")

    sections: list[tuple[str, str]] = []
    for name, content in matches:
        name_stripped = name.strip()
        content_stripped = content.strip()
        if not name_stripped or not content_stripped:
            raise SectionRewriteError("Empty section name or content in SECTION block")
        sections.append((name_stripped, content_stripped))

    return sections


def normalize_section_name(name: str) -> str:
    """Normalize section name for comparison."""
    return name.strip().lower()


def find_matching_section(
    section_name: str,
    section_map: dict[str, tuple[int, int, int]],
) -> tuple[int, int, int] | None:
    """Find matching section using exact match, then normalized match.

    Returns (level, start_idx, end_idx) or None if not found.
    """
    # Try exact match first
    if section_name in section_map:
        return section_map[section_name]

    # Try normalized match
    normalized_target = normalize_section_name(section_name)
    for heading_text, section_info in section_map.items():
        if normalize_section_name(heading_text) == normalized_target:
            return section_info

    return None


def extract_section_heading(replacement_text: str) -> str | None:
    """Extract the heading from replacement text to determine section level and title."""
    lines = replacement_text.split("\n")
    for line in lines:
        heading_match = re.match(r"^(#+)\s+(.+)$", line)
        if heading_match:
            return line
    return None


def find_insertion_point(
    section_name: str,
    sections: list[tuple[str, int, int, int]],
) -> int:
    """Find where to insert a new section.

    Looks for sections that might come after this one based on common patterns.
    Returns line index where the new section should be inserted.
    """
    # Common section ordering patterns (extended for various document types)
    common_order = [
        "abstract",
        "introduction",
        "overview",
        "project overview",
        "background",
        "literature review",
        "team structure",
        "technology stack",
        "methodology",
        "details",
        "project phases",
        "findings",
        "results",
        "discussion",
        "discussion points",
        "risk management",
        "budget summary",
        "budget",
        "communication plan",
        "conclusion",
        "acknowledgments",
        "action items",
        "next steps",
        "next meeting",
        "appendices",
        "references",
    ]

    normalized_name = normalize_section_name(section_name)

    # Try to find logical insertion point based on common ordering
    try:
        target_idx = common_order.index(normalized_name)
        # Find the next section in the document that comes after this in common_order
        for heading_text, _level, start_idx, _end_idx in sections:
            normalized_heading = normalize_section_name(heading_text)
            if normalized_heading in common_order:
                heading_idx = common_order.index(normalized_heading)
                if heading_idx > target_idx:
                    return start_idx
    except ValueError:
        pass

    # Fallback: insert at the end of the document
    if sections:
        return sections[-1][3]  # After last section
    return 0


def build_section_map(text: str) -> dict[str, tuple[int, int, int]]:
    """Build mapping from heading text to (level, start_idx, end_idx)."""
    sections = split_sections(text)
    section_map: dict[str, tuple[int, int, int]] = {}
    for heading_text, level, start_idx, end_idx in sections:
        section_map[heading_text] = (level, start_idx, end_idx)
    return section_map


def apply_single_replacement(doc: str, section_name: str, replacement_text: str) -> str:
    """Apply a single section replacement or insertion to the document.

    Re-parses section boundaries from current document state to ensure correct indices.
    """
    lines = doc.split("\n")
    section_map = build_section_map(doc)
    section_info = find_matching_section(section_name, section_map)

    if section_info is not None:
        _, start_idx, end_idx = section_info
        replacement_lines = replacement_text.split("\n")
        lines[start_idx:end_idx] = replacement_lines
    else:
        sections = split_sections(doc)
        insertion_point = find_insertion_point(section_name, sections)
        insertion_lines = replacement_text.split("\n")
        lines[insertion_point:insertion_point] = ["", *insertion_lines]

    return "\n".join(lines)


def apply_section_replacements(initial: str, replacements: list[tuple[str, str]]) -> str:
    """Apply section replacements sequentially, re-parsing after each operation."""
    result = initial
    for section_name, replacement_text in replacements:
        result = apply_single_replacement(result, section_name, replacement_text)
    return result


class SectionRewriteAlgorithm(Algorithm):
    """LLM outputs only modified sections wrapped in SECTION blocks."""

    name = "section_rewrite"
    description = "Rewrite individual markdown sections by heading"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        # Pass 1: Initial LLM call
        output, usage = await call_llm(model, user_prompt, system_prompt)

        try:
            section_replacements = parse_section_blocks(output)
        except SectionRewriteError as e:
            # Pass 2: Retry with parse error context
            retry_prompt = pm.get(
                "retry.jinja2",
                current=initial,
                changes=changes,
                parse_error=str(e),
            )
            retry_output, retry_usage = await call_llm(model, retry_prompt, system_prompt)
            usage = usage + retry_usage

            try:
                section_replacements = parse_section_blocks(retry_output)
            except SectionRewriteError as retry_error:
                # Retry also failed
                return AlgorithmResult(
                    output=None,
                    success=False,
                    error=f"Parse failed after retry: {retry_error}",
                    usage=usage,
                    warnings=[f"Initial parse error: {e}"],
                )

        # Apply all sections
        result = apply_section_replacements(initial, section_replacements)

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
        )

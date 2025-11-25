"""Scoring system for evaluating diff algorithm output quality."""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class DiffScore:
    """Score representing how well the output matches expected."""

    # Binary
    exact_match: bool  # output == expected (after normalization)

    # Line-based metrics
    lines_correct: int  # Lines that match expected
    lines_missing: int  # Lines in expected but not in output
    lines_extra: int  # Lines in output but not in expected
    lines_total_expected: int  # Total lines in expected

    # Similarity (0.0 - 1.0)
    line_similarity: float  # Jaccard similarity on lines
    char_similarity: float  # difflib.SequenceMatcher ratio

    # Structural
    headers_preserved: bool  # All headers from expected present
    header_order_correct: bool  # Headers in same order

    # The diff itself (for inspection)
    unified_diff: str  # Unified diff showing differences

    @property
    def overall_score(self) -> float:
        """Weighted combination of metrics (0.0 - 1.0)."""
        if self.exact_match:
            return 1.0

        # Weight: 50% line similarity, 30% char similarity, 20% structure
        structure_score = (
            (1.0 if self.headers_preserved else 0.0) + (1.0 if self.header_order_correct else 0.0)
        ) / 2

        return 0.5 * self.line_similarity + 0.3 * self.char_similarity + 0.2 * structure_score

    @property
    def passed(self) -> bool:
        """Whether this counts as a pass.

        Pass if exact match OR high similarity (>= 0.96) with minimal missing content.
        """
        if self.exact_match:
            return True
        # Allow near-perfect matches (minor differences only)
        if self.overall_score >= 0.98 and self.lines_missing == 0:
            return True
        # Allow high-quality matches with very few missing lines
        return self.overall_score >= 0.96 and self.lines_missing <= 2


class DiffScorer:
    """Calculate diff scores between output and expected."""

    def score(self, output: str | None, expected: str) -> DiffScore:
        """Calculate comprehensive diff score.

        Args:
            output: Algorithm output (None if algorithm failed)
            expected: Expected final document

        Returns:
            DiffScore with all metrics calculated
        """
        # Handle None output (algorithm failure)
        if output is None:
            return DiffScore(
                exact_match=False,
                lines_correct=0,
                lines_missing=len(expected.splitlines()),
                lines_extra=0,
                lines_total_expected=len(expected.splitlines()),
                line_similarity=0.0,
                char_similarity=0.0,
                headers_preserved=False,
                header_order_correct=False,
                unified_diff="(no output to compare)",
            )

        # Normalize both texts
        output_norm = self.normalize(output)
        expected_norm = self.normalize(expected)

        # Exact match check
        exact_match = output_norm == expected_norm

        # Line-based metrics
        output_lines = set(output_norm.splitlines())
        expected_lines = set(expected_norm.splitlines())

        lines_correct = len(output_lines & expected_lines)
        lines_missing = len(expected_lines - output_lines)
        lines_extra = len(output_lines - expected_lines)
        lines_total_expected = len(expected_lines)

        # Jaccard similarity on lines
        union = output_lines | expected_lines
        line_similarity = len(output_lines & expected_lines) / len(union) if union else 1.0

        # Character-level similarity using SequenceMatcher
        char_similarity = difflib.SequenceMatcher(None, output_norm, expected_norm).ratio()

        # Structural checks (headers)
        output_headers = self._extract_headers(output_norm)
        expected_headers = self._extract_headers(expected_norm)

        headers_preserved = set(expected_headers).issubset(set(output_headers))
        header_order_correct = self._check_header_order(output_headers, expected_headers)

        # Generate unified diff
        unified_diff = self.generate_diff(output_norm, expected_norm)

        return DiffScore(
            exact_match=exact_match,
            lines_correct=lines_correct,
            lines_missing=lines_missing,
            lines_extra=lines_extra,
            lines_total_expected=lines_total_expected,
            line_similarity=line_similarity,
            char_similarity=char_similarity,
            headers_preserved=headers_preserved,
            header_order_correct=header_order_correct,
            unified_diff=unified_diff,
        )

    def generate_diff(self, output: str, expected: str) -> str:
        """Generate unified diff for inspection.

        Args:
            output: Algorithm output (normalized)
            expected: Expected output (normalized)

        Returns:
            Unified diff string
        """
        output_lines = output.splitlines(keepends=True)
        expected_lines = expected.splitlines(keepends=True)

        # Ensure last lines have newlines for proper diff
        if output_lines and not output_lines[-1].endswith("\n"):
            output_lines[-1] += "\n"
        if expected_lines and not expected_lines[-1].endswith("\n"):
            expected_lines[-1] += "\n"

        diff = difflib.unified_diff(
            expected_lines,
            output_lines,
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )

        return "".join(diff)

    def normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        lines = text.replace("\r\n", "\n").split("\n")
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]
        result = "\n".join(lines)
        # Normalize Unicode hyphens to ASCII
        result = result.replace("\u2011", "-").replace("\u2010", "-").replace("\u2212", "-")
        return result

    def _extract_headers(self, text: str) -> list[str]:
        """Extract markdown headers from text.

        Returns list of header lines (including # prefix).
        """
        return [line for line in text.splitlines() if line.startswith("#")]

    def _check_header_order(self, output_headers: list[str], expected_headers: list[str]) -> bool:
        """Check if headers appear in the correct order.

        Returns True if all expected headers appear in output in the same order.
        """
        if not expected_headers:
            return True

        # Find positions of expected headers in output
        positions: list[int] = []
        for eh in expected_headers:
            try:
                pos = output_headers.index(eh)
                positions.append(pos)
            except ValueError:
                # Header not found
                return False

        # Check if positions are monotonically increasing
        return positions == sorted(positions)


# Global scorer instance for convenience
_scorer = DiffScorer()


def score_output(output: str | None, expected: str) -> DiffScore:
    """Score algorithm output against expected result.

    Convenience function using global scorer.
    """
    return _scorer.score(output, expected)


def generate_diff(output: str, expected: str) -> str:
    """Generate unified diff between output and expected.

    Convenience function using global scorer.
    """
    return _scorer.generate_diff(
        _scorer.normalize(output),
        _scorer.normalize(expected),
    )

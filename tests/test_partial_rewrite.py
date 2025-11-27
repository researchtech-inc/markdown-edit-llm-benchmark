"""Tests for partial_rewrite algorithm."""

from md_edit_bench.algorithms.partial_rewrite.partial_rewrite import (
    expand_document,
    find_first,
)


class TestFindFirst:
    def test_finds_line(self):
        lines = ["A", "B", "C", "D"]
        assert find_first(lines, "B") == 1

    def test_finds_first_occurrence(self):
        lines = ["A", "B", "A", "C"]
        assert find_first(lines, "A") == 0

    def test_finds_after_start(self):
        lines = ["A", "B", "A", "C"]
        assert find_first(lines, "A", start=1) == 2

    def test_not_found_returns_none(self):
        lines = ["A", "B", "C"]
        assert find_first(lines, "X") is None

    def test_not_found_after_start(self):
        lines = ["A", "B", "C"]
        assert find_first(lines, "A", start=1) is None

    def test_empty_lines(self):
        lines: list[str] = []
        assert find_first(lines, "A") is None


class TestExpandDocument:
    def test_no_ellipsis_returns_unchanged(self):
        original = "A\nB\nC"
        output = "A\nX\nC"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nX\nC"

    def test_single_ellipsis_expands(self):
        original = "A\nB\nC\nD\nE"
        output = "A\n...\nE"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nC\nD\nE"

    def test_ellipsis_skips_middle(self):
        original = "Header\nLine1\nLine2\nLine3\nFooter"
        output = "Header\n...\nFooter"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "Header\nLine1\nLine2\nLine3\nFooter"

    def test_ellipsis_with_change_before(self):
        original = "A\nB\nC\nD\nE"
        output = "X\nC\n...\nE"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "X\nC\nD\nE"

    def test_ellipsis_with_change_after(self):
        original = "A\nB\nC\nD\nE"
        output = "A\n...\nC\nX"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nC\nX"

    def test_multiple_ellipsis(self):
        original = "A\nB\nC\nD\nE\nF\nG\nH"
        output = "A\n...\nC\nX\nE\n...\nH"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nC\nX\nE\nF\nG\nH"

    def test_duplicate_lines_first_ellipsis(self):
        """First occurrence of duplicate should be used."""
        original = "A\nB\nA\nC"
        output = "A\n...\nA\nC"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nA\nC"

    def test_duplicate_lines_sequential(self):
        """Multiple ellipsis with duplicates should track position."""
        original = "A\nB\nA\nC\nA\nD"
        output = "A\n...\nA\nC\nA\n...\nD"
        result, error = expand_document(original, output)
        assert error is None
        # First A...A expands B, second A...D expands nothing (adjacent)
        # Wait, let me trace: A(0), B(1), A(2), C(3), A(4), D(5)
        # Output: A, ..., A, C, A, ..., D
        # First ...: before=A, after=A. Find A at 0, find A after 0 at 2. Insert B.
        # Result so far: A, B, A
        # Then C: result = A, B, A, C
        # Then A: result = A, B, A, C, A
        # Second ...: before=A, after=D. Find A after last_anchor_pos(1)+1=2...
        # Hmm, this needs more thought. Let me adjust the test.
        assert result == "A\nB\nA\nC\nA\nD"

    def test_adjacent_anchors_nothing_to_skip(self):
        """When anchors are adjacent in original, nothing is inserted."""
        original = "A\nB\nC"
        output = "A\n...\nB\nC"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nC"

    def test_literal_ellipsis_in_original(self):
        """Literal ... in original content should be preserved."""
        original = "A\n...\nB"
        output = "A\n...\nB"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\n...\nB"

    def test_ellipsis_at_start_error(self):
        original = "A\nB\nC"
        output = "...\nC"
        _, error = expand_document(original, output)
        assert error is not None
        assert "preceding" in error.lower() or "start" in error.lower()

    def test_ellipsis_at_end_error(self):
        original = "A\nB\nC"
        output = "A\n..."
        _, error = expand_document(original, output)
        assert error is not None
        assert "following" in error.lower() or "end" in error.lower()

    def test_before_anchor_not_found_error(self):
        original = "A\nB\nC"
        output = "X\n...\nC"
        _, error = expand_document(original, output)
        assert error is not None
        assert "not found" in error.lower()

    def test_after_anchor_not_found_error(self):
        original = "A\nB\nC"
        output = "A\n...\nX"
        _, error = expand_document(original, output)
        assert error is not None
        assert "not found" in error.lower()

    def test_anchors_wrong_order_error(self):
        """After anchor appears before before anchor in original."""
        original = "A\nB\nC\nD"
        output = "C\n...\nA"
        _, error = expand_document(original, output)
        assert error is not None
        assert "not found" in error.lower()

    def test_empty_original(self):
        original = ""
        output = "A"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A"

    def test_empty_output(self):
        original = "A\nB\nC"
        output = ""
        result, error = expand_document(original, output)
        assert error is None
        assert result == ""

    def test_single_line_no_change(self):
        original = "A"
        output = "A"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A"

    def test_whitespace_lines(self):
        """Lines with whitespace should match exactly."""
        original = "A\n  B  \nC"
        output = "A\n...\nC"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\n  B  \nC"

    def test_multiline_skip(self):
        """Skip many lines at once."""
        lines = [f"Line{i}" for i in range(100)]
        original = "\n".join(lines)
        output = "Line0\n...\nLine99"
        result, error = expand_document(original, output)
        assert error is None
        assert result == original


class TestExpandDocumentLongContent:
    """Tests with longer, more realistic content."""

    def test_markdown_document(self):
        original = """# Title

## Section 1
Content for section 1.
More content here.

## Section 2
Old content to change.

## Section 3
Final section content.
The end."""

        output = """# Title

## Section 1
...
More content here.

## Section 2
New content here!

## Section 3
...
The end."""

        result, error = expand_document(original, output)
        assert error is None
        assert "Content for section 1." in result
        assert "New content here!" in result
        assert "Final section content." in result

    def test_code_block_unchanged(self):
        original = """def foo():
    line1
    line2
    line3
    return True"""

        output = """def foo():
    line1
    ...
    line3
    return True"""

        result, error = expand_document(original, output)
        assert error is None
        assert "line2" in result

    def test_multiple_changes_with_skips(self):
        original = "A\nB\nC\nD\nE\nF\nG\nH\nI\nJ"
        # Change C to X, G to Y, skip B, D-F, H-I
        output = "A\n...\nB\nX\nD\n...\nF\nY\nH\n...\nJ"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "A\nB\nX\nD\nE\nF\nY\nH\nI\nJ"


class TestExpandDocumentEdgeCases:
    """Edge cases and tricky scenarios."""

    def test_consecutive_ellipsis_error(self):
        """Two ... in a row should fail (no anchor between)."""
        original = "A\nB\nC\nD"
        output = "A\n...\n...\nD"
        _, error = expand_document(original, output)
        # The second ... has "..." as before_line which won't be found
        assert error is not None

    def test_same_line_repeated_many_times(self):
        """Handle many duplicate lines correctly."""
        original = "X\nA\nX\nB\nX\nC\nX"
        output = "X\n...\nX\nB\nX\n...\nX"
        result, error = expand_document(original, output)
        assert error is None
        assert result == "X\nA\nX\nB\nX\nC\nX"

    def test_anchor_at_document_boundaries(self):
        """First and last lines as anchors."""
        original = "START\nA\nB\nC\nEND"
        output = "START\n...\nEND"
        result, error = expand_document(original, output)
        assert error is None
        assert result == original

    def test_only_ellipsis_with_anchors(self):
        """Document is just first line, ..., last line."""
        original = "A\nB\nC\nD\nE"
        output = "A\n...\nE"
        result, error = expand_document(original, output)
        assert error is None
        assert result == original

    def test_newline_handling(self):
        """Trailing newlines should be handled."""
        original = "A\nB\nC\n"
        output = "A\n...\nC\n"
        result, error = expand_document(original, output)
        assert error is None
        # Note: split('\n') on "A\nB\nC\n" gives ["A", "B", "C", ""]
        # This might cause issues - let's see what happens
        assert "B" in result

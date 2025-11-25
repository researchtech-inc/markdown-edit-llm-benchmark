"""Data models for diff benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class LLMCall:
    """Record of a single LLM API call."""

    model: str
    request: str
    response: str


@dataclass
class LLMUsage:
    """Usage information from LLM API calls."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    calls: list[LLMCall] = field(default_factory=list)

    def __add__(self, other: LLMUsage) -> LLMUsage:
        """Accumulate usage from multiple calls."""
        return LLMUsage(
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cost_usd=self.cost_usd + other.cost_usd,
            calls=self.calls + other.calls,
        )


@dataclass
class AlgorithmResult:
    """Result from an algorithm's apply() method."""

    output: str | None  # The final document (None if failed)
    success: bool  # Did algorithm complete without error
    error: str | None  # Error message if failed
    usage: LLMUsage  # Accumulated usage from all LLM calls


@dataclass
class Fixture:
    """A test case for benchmarking."""

    name: str  # e.g., "simple/add_paragraph"
    initial: str  # Initial document content
    changes: str  # Natural language change request
    expected: str  # Expected final document


@dataclass
class TestResult:
    """Result of running one algorithm on one fixture."""

    fixture: str  # e.g., "simple/add_paragraph"
    algorithm: str  # e.g., "git_diff"
    model: str | None  # e.g., "gpt-4o" or None for morph

    # Algorithm output
    algorithm_result: AlgorithmResult

    # Comparison with expected (filled in by scorer)
    exact_match: bool = False
    similarity_score: float = 0.0
    lines_missing: int = 0
    lines_extra: int = 0
    diff_from_expected: str = ""

    # Timing
    duration_seconds: float = 0.0

    @property
    def passed(self) -> bool:
        """Whether this test passed (exact match required)."""
        return self.algorithm_result.success and self.exact_match

    @property
    def cost_usd(self) -> float:
        """Total cost in USD."""
        return self.algorithm_result.usage.cost_usd


@dataclass
class BenchmarkRun:
    """Results from a complete benchmark run."""

    timestamp: datetime
    results: list[TestResult] = field(default_factory=list)

    def by_algorithm(self) -> dict[str, list[TestResult]]:
        """Group results by algorithm name."""
        grouped: dict[str, list[TestResult]] = {}
        for r in self.results:
            grouped.setdefault(r.algorithm, []).append(r)
        return grouped

    def by_model(self) -> dict[str | None, list[TestResult]]:
        """Group results by model."""
        grouped: dict[str | None, list[TestResult]] = {}
        for r in self.results:
            grouped.setdefault(r.model, []).append(r)
        return grouped

    def by_fixture(self) -> dict[str, list[TestResult]]:
        """Group results by fixture name."""
        grouped: dict[str, list[TestResult]] = {}
        for r in self.results:
            grouped.setdefault(r.fixture, []).append(r)
        return grouped

    @property
    def total_passed(self) -> int:
        """Total number of passed tests."""
        return sum(1 for r in self.results if r.passed)

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.results)

    @property
    def total_cost_usd(self) -> float:
        """Total cost across all tests."""
        return sum(r.cost_usd for r in self.results)

    @property
    def total_duration_seconds(self) -> float:
        """Total duration across all tests."""
        return sum(r.duration_seconds for r in self.results)


def discover_fixtures(base_dir: Path) -> list[Fixture]:
    """Find all test cases by looking for .initial.md files."""
    fixtures: list[Fixture] = []

    for initial_file in sorted(base_dir.rglob("*.initial.md")):
        # Extract name without .initial.md suffix
        name_part = initial_file.name.replace(".initial.md", "")
        category = initial_file.parent.name

        # Find corresponding files
        changes_file = initial_file.parent / f"{name_part}.changes.md"
        final_file = initial_file.parent / f"{name_part}.final.md"

        if not changes_file.exists():
            continue
        if not final_file.exists():
            continue

        fixtures.append(
            Fixture(
                name=f"{category}/{name_part}",
                initial=initial_file.read_text(encoding="utf-8"),
                changes=changes_file.read_text(encoding="utf-8"),
                expected=final_file.read_text(encoding="utf-8"),
            )
        )

    return fixtures

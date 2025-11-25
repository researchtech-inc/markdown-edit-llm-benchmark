"""Algorithm base class and registry for diff benchmarks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from md_edit_bench.models import AlgorithmResult

# Registry of all algorithms
_algorithms: dict[str, type[Algorithm]] = {}


def register_algorithm(cls: type[Algorithm]) -> type[Algorithm]:
    """Decorator to register an algorithm class."""
    _algorithms[cls.name] = cls
    return cls


def get_algorithm(name: str) -> Algorithm:
    """Get an algorithm instance by name."""
    if name not in _algorithms:
        raise ValueError(f"Unknown algorithm: {name}. Available: {list(_algorithms.keys())}")
    return _algorithms[name]()


def get_all_algorithms() -> list[Algorithm]:
    """Get instances of all registered algorithms."""
    return [cls() for cls in _algorithms.values()]


def list_algorithm_names() -> list[str]:
    """Get names of all registered algorithms."""
    return list(_algorithms.keys())


class Algorithm(ABC):
    """Base class for diff algorithms."""

    # Subclasses must define these
    name: str  # Unique identifier (e.g., "git_diff")
    description: str  # Human-readable description
    accepts_model: bool  # Whether model can be specified
    default_model: str | None = None  # Default model if accepts_model=True

    @abstractmethod
    async def apply(
        self,
        initial: str,
        changes: str,
        model: str | None = None,
    ) -> AlgorithmResult:
        """Apply changes to initial document.

        Args:
            initial: Initial document content
            changes: Natural language description of changes to make
            model: Model to use (ignored if accepts_model=False)

        Returns:
            AlgorithmResult with output, success status, and usage info
        """
        pass

    def get_models_to_test(self) -> list[str | None]:
        """Return list of models to test with this algorithm.

        Override in subclass to test multiple models.
        """
        if not self.accepts_model:
            return [None]  # Only test once, no model
        return [self.default_model]


# Import algorithms to register them
from md_edit_bench.algorithms.aider_diff_fenced import AiderDiffFencedAlgorithm
from md_edit_bench.algorithms.aider_diff_fenced_v2 import AiderDiffFencedV2Algorithm
from md_edit_bench.algorithms.aider_editblock import AiderEditBlockAlgorithm
from md_edit_bench.algorithms.aider_patch import AiderPatchAlgorithm
from md_edit_bench.algorithms.aider_udiff import AiderUdiffAlgorithm
from md_edit_bench.algorithms.codex_patch import CodexPatchAlgorithm
from md_edit_bench.algorithms.full_rewrite import FullRewriteAlgorithm
from md_edit_bench.algorithms.git_diff import GitDiffAlgorithm
from md_edit_bench.algorithms.json_ops import JsonOpsAlgorithm
from md_edit_bench.algorithms.morph import MorphAlgorithm
from md_edit_bench.algorithms.search_replace import SearchReplaceAlgorithm
from md_edit_bench.algorithms.section_rewrite import SectionRewriteAlgorithm
from md_edit_bench.algorithms.str_replace_editor import StrReplaceEditorAlgorithm
from md_edit_bench.algorithms.udiff_tagged import UdiffTaggedAlgorithm

__all__ = [
    "AiderDiffFencedAlgorithm",
    "AiderDiffFencedV2Algorithm",
    "AiderEditBlockAlgorithm",
    "AiderPatchAlgorithm",
    "AiderUdiffAlgorithm",
    "Algorithm",
    "CodexPatchAlgorithm",
    "FullRewriteAlgorithm",
    "GitDiffAlgorithm",
    "JsonOpsAlgorithm",
    "MorphAlgorithm",
    "SearchReplaceAlgorithm",
    "SectionRewriteAlgorithm",
    "StrReplaceEditorAlgorithm",
    "UdiffTaggedAlgorithm",
    "get_algorithm",
    "get_all_algorithms",
    "list_algorithm_names",
    "register_algorithm",
]

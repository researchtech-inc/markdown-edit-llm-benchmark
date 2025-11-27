"""Algorithm registry for diff benchmarks."""

from md_edit_bench.algorithms.aider_diff_fenced import AiderDiffFencedAlgorithm
from md_edit_bench.algorithms.aider_editblock import AiderEditBlockAlgorithm
from md_edit_bench.algorithms.aider_patch import AiderPatchAlgorithm
from md_edit_bench.algorithms.aider_udiff import AiderUdiffAlgorithm
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.algorithms.codex_patch import CodexPatchAlgorithm
from md_edit_bench.algorithms.full_rewrite import FullRewriteAlgorithm
from md_edit_bench.algorithms.git_diff import GitDiffAlgorithm
from md_edit_bench.algorithms.json_ops import JsonOpsAlgorithm
from md_edit_bench.algorithms.morph import MorphAlgorithm
from md_edit_bench.algorithms.partial_rewrite import PartialRewriteAlgorithm
from md_edit_bench.algorithms.search_replace import SearchReplaceAlgorithm
from md_edit_bench.algorithms.section_rewrite import SectionRewriteAlgorithm
from md_edit_bench.algorithms.str_replace_editor import StrReplaceEditorAlgorithm
from md_edit_bench.algorithms.udiff_tagged import UdiffTaggedAlgorithm

ALGORITHMS: list[type[Algorithm]] = [
    AiderDiffFencedAlgorithm,
    AiderEditBlockAlgorithm,
    AiderPatchAlgorithm,
    AiderUdiffAlgorithm,
    CodexPatchAlgorithm,
    FullRewriteAlgorithm,
    GitDiffAlgorithm,
    JsonOpsAlgorithm,
    MorphAlgorithm,
    PartialRewriteAlgorithm,
    SearchReplaceAlgorithm,
    SectionRewriteAlgorithm,
    StrReplaceEditorAlgorithm,
    UdiffTaggedAlgorithm,
]

_algorithms_by_name: dict[str, type[Algorithm]] = {cls.name: cls for cls in ALGORITHMS}


def get_algorithm(name: str) -> Algorithm:
    """Get an algorithm instance by name."""
    if name not in _algorithms_by_name:
        raise ValueError(
            f"Unknown algorithm: {name}. Available: {list(_algorithms_by_name.keys())}"
        )
    return _algorithms_by_name[name]()


def get_all_algorithms() -> list[Algorithm]:
    """Get instances of all registered algorithms."""
    return [cls() for cls in ALGORITHMS]


def list_algorithm_names() -> list[str]:
    """Get names of all registered algorithms."""
    return list(_algorithms_by_name.keys())


__all__ = [
    "ALGORITHMS",
    "AiderDiffFencedAlgorithm",
    "AiderEditBlockAlgorithm",
    "AiderPatchAlgorithm",
    "AiderUdiffAlgorithm",
    "Algorithm",
    "CodexPatchAlgorithm",
    "FullRewriteAlgorithm",
    "GitDiffAlgorithm",
    "JsonOpsAlgorithm",
    "MorphAlgorithm",
    "PartialRewriteAlgorithm",
    "SearchReplaceAlgorithm",
    "SectionRewriteAlgorithm",
    "StrReplaceEditorAlgorithm",
    "UdiffTaggedAlgorithm",
    "get_algorithm",
    "get_all_algorithms",
    "list_algorithm_names",
]

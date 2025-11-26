"""Base class for diff algorithms."""

from abc import ABC, abstractmethod

from md_edit_bench.models import AlgorithmResult


class Algorithm(ABC):
    """Base class for diff algorithms."""

    name: str
    description: str

    @abstractmethod
    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        """Apply changes to initial document."""
        pass

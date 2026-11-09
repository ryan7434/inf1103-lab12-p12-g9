from abc import ABC, abstractmethod
from typing import Any


class ResponseValidator(ABC):
    """Abstract base for checking AI output.

    filter_valid() is shared behaviour; each subclass supplies its own is_valid().
    """

    def filter_valid(self, items: list) -> list:
        return [item for item in items if self.is_valid(item)]

    @abstractmethod
    def is_valid(self, item: Any) -> bool:
        """Return True if one item has the structure this validator requires."""

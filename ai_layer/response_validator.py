from abc import ABC, abstractmethod
from typing import Any

# Abstract base class for "checkers" of AI output.
# The shared filtering logic lives here; each subclass only decides what "valid" means.
class ResponseValidator(ABC):
    """Abstract base for checking AI output.

    filter_valid() is shared behaviour; each subclass supplies its own is_valid().
    """
     # Keep only the items that pass is_valid(), in their original order.
    def filter_valid(self, items: list) -> list:
        return [item for item in items if self.is_valid(item)]
    # Each subclass must define the rules for one item.
    @abstractmethod
    def is_valid(self, item: Any) -> bool:
        """Return True if one item has the structure this validator requires."""

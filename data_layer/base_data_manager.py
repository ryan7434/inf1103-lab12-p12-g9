from abc import ABC, abstractmethod


class BaseDataManager(ABC):
    """Abstract Base Class (Interface) defining the contract for data persistence layers."""

    @abstractmethod
    def init_storage(self) -> bool:
        """Initialize underlying data storage."""
        pass

    @abstractmethod
    def save_record(self, record_dict: dict) -> bool:
        """Save a new record to storage."""
        pass

    @abstractmethod
    def load_records(self) -> list:
        """Load all saved records."""
        pass

    @abstractmethod
    def query_by_ingredient(self, ingredient_keyword: str) -> list:
        """Query records by ingredient keyword."""
        pass

    @abstractmethod
    def query_by_max_time(self, max_mins: int | float) -> list:
        """Query records by maximum cooking time."""
        pass
from abc import ABC, abstractmethod
import json
import os
import tempfile


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


class JsonDataManager(BaseDataManager):
    """Concrete implementation of BaseDataManager using a local JSON file backend."""

    def __init__(self, file_path: str = "recipes_history.json"):
        # Encapsulation: Storing file path as a protected attribute
        self._file_path = file_path
        self.init_storage()

    def init_storage(self) -> bool:
        """Initializes the JSON file with an empty list if it does not exist or is empty."""
        if not os.path.exists(self._file_path) or os.path.getsize(self._file_path) == 0:
            try:
                with open(self._file_path, mode="w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)
                return True
            except Exception:
                return False
        return True

    def save_record(self, record_dict: dict) -> bool:
        """Adds a recipe without overwriting invalid existing history."""
        if not isinstance(record_dict, dict) or not self.init_storage():
            return False

        try:
            with open(self._file_path, encoding="utf-8") as f:
                records = json.load(f)

            if not (isinstance(records, list) and all(isinstance(r, dict) for r in records)):
                return False

            # Serialize before opening for write, so a failure can't truncate the file.
            output = json.dumps(
                records + [record_dict],
                indent=4,
                ensure_ascii=False,
                allow_nan=False,
            )

            #write separately before replacing the existing history.
            directory = os.path.dirname(os.path.abspath(self._file_path))
            temporary_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=directory,
                    prefix=".recipes-history-",
                    suffix=".tmp",
                    delete=False,
                ) as temporary_file:
                    temporary_path = temporary_file.name
                    temporary_file.write(output)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())

                os.replace(temporary_path, self._file_path)
                return True
            finally:
                if temporary_path is not None:
                    try:
                        os.unlink(temporary_path)
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
        except (OSError, TypeError, ValueError):
            return False

    def load_records(self) -> list:
        """Loads all saved recipe records into memory on system startup or query."""
        if not os.path.exists(self._file_path):
            self.init_storage()
            return []

        try:
            with open(self._file_path, mode="r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                records = json.loads(content)
            
            if isinstance(records, list) and all(isinstance(record, dict) for record in records):
                return records

            return []
        except (json.JSONDecodeError, Exception):
            return []

    def query_by_ingredient(self, ingredient_keyword: str) -> list:
        """Filters database records by a specific ingredient name."""
        all_records = self.load_records()
        matching_records = []
        keyword_clean = ingredient_keyword.strip().lower()

        for rec in all_records:
            used_ing = rec.get("used_ingredients", [])
            if isinstance(used_ing, list):
                if any(keyword_clean in str(item).lower() for item in used_ing):
                    matching_records.append(rec)
            elif isinstance(used_ing, str):
                if keyword_clean in used_ing.lower():
                    matching_records.append(rec)

        return matching_records

    def query_by_max_time(self, max_mins: int | float) -> list:
        """Filters database records by maximum cooking time limit."""
        all_records = self.load_records()
        matching_records = []

        for rec in all_records:
            time_val = rec.get("cooking_time_mins", 0)
            if isinstance(time_val, (int, float)) and time_val <= max_mins:
                matching_records.append(rec)

        return matching_records
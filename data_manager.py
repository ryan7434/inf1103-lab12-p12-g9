import json
import os

# Primary database JSON file name
DATA_FILE = "recipes_history.json"


def init_data_storage(file_path=DATA_FILE):
    """Initializes the JSON file with an empty list if it does not exist or is empty.

    Prevents crashing on initial run.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        try:
            with open(file_path, mode="w", encoding="utf-8") as f:
                json.dump([], f, indent=4)
        except Exception:
            return False
    return True


def save_processed_record(record_dict, file_path=DATA_FILE):
    """Adds a recipe without overwriting invalid existing history."""
    if not isinstance(record_dict, dict) or not init_data_storage(file_path):
        return False

    try:
        with open(file_path, encoding="utf-8") as f:
            records = json.load(f)

        if not (
            isinstance(records, list)
            and all(isinstance(r, dict) for r in records)
        ):
            return False

        # Serialise before opening for write, so a failure can't truncate the file.
        output = json.dumps(
            records + [record_dict],
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output)
        return True
    except (OSError, TypeError, ValueError):
        return False


def load_all_records(file_path=DATA_FILE):
    """Loads all saved recipe records into memory on system startup or query.

    Handles missing or corrupt files safely without crashing.
    """
    if not os.path.exists(file_path):
        init_data_storage(file_path)
        return []

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            records = json.loads(content)
        if (
            isinstance(records, list)
            and all(isinstance(record, dict) for record in records)
        ):
            return records

        return []
    except (json.JSONDecodeError, Exception):
        return []


def query_records_by_ingredient(ingredient_keyword, file_path=DATA_FILE):
    """Filters database records by a specific ingredient name."""
    all_records = load_all_records(file_path)
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


def query_records_by_max_time(max_mins, file_path=DATA_FILE):
    """Filters database records by maximum cooking time limit."""
    all_records = load_all_records(file_path)
    matching_records = []

    for rec in all_records:
        time_val = rec.get("cooking_time_mins", 0)
        # Handle cases where it might be stored as int or float
        if isinstance(time_val, (int, float)) and time_val <= max_mins:
            matching_records.append(rec)

    return matching_records
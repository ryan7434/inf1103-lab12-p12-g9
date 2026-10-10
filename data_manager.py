import csv
import json
import os

# Primary database CSV file name
DATA_FILE = "recipes_history.csv"

# Columns matching AI outputs, user inputs, and logic criteria
FIELDNAMES = [
    "record_id",
    "timestamp",
    "dish_name",
    "matched_ingredients_count",
    "used_ingredients",
    "missing_ingredients",
    "seasonings_suggested",
    "cooking_time_mins",
    "servings",
    "cuisine",
    "meal_type",
    "taste_preference",
    "dietary_restrictions",
    "ai_insight",
    "instructions",
]


def init_data_storage(file_path=DATA_FILE):
    """Initializes the CSV file with headers if it does not exist or is empty.

    Prevents crashing on initial run.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
        except Exception:
            return False
    return True


def serialize_field(value):
    """Converts lists or dictionaries to JSON strings so they store cleanly in CSV cells."""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value) if value is not None else ""


def deserialize_field(value):
    """Parses JSON string values back into Python lists or dicts upon loading."""
    if not value:
        return ""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def save_processed_record(record_dict, file_path=DATA_FILE):
    """Appends a single processed recipe record to the CSV database file."""
    init_data_storage(file_path)

    row_data = {}
    for field in FIELDNAMES:
        val = record_dict.get(field, "")
        row_data[field] = serialize_field(val)

    try:
        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row_data)
        return True
    except Exception:
        return False


def load_all_records(file_path=DATA_FILE):
    """Loads all saved recipe records into memory on system startup or query.

    Handles missing or corrupt files safely without crashing.
    """
    if not os.path.exists(file_path):
        init_data_storage(file_path)
        return []

    records = []
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames != FIELDNAMES:
                return []

            for row in reader:
                deserialized_row = {}
                for key, val in row.items():
                    deserialized_row[key] = deserialize_field(val)

                # Format numeric fields
                if "matched_ingredients_count" in deserialized_row:
                    try:
                        deserialized_row["matched_ingredients_count"] = int(
                            deserialized_row["matched_ingredients_count"]
                        )
                    except ValueError:
                        pass

                if "cooking_time_mins" in deserialized_row:
                    try:
                        deserialized_row["cooking_time_mins"] = int(
                            deserialized_row["cooking_time_mins"]
                        )
                    except ValueError:
                        pass

                records.append(deserialized_row)
        return records
    except Exception:
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
        if isinstance(time_val, int) and time_val <= max_mins:
            matching_records.append(rec)

    return matching_records
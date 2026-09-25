"""
io_manager -> ai_manager -> logic_manager -> data_manager

Responsibilities (per project spec, "must implement"):
  1. Build a prompt from the input record.
  2. Call the AI API and parse the response.
  3. Validate the response schema - reject/retry on malformed output.
  4. Handle API failure gracefully - log and continue, NEVER crash.
  5. Zero domain logic here - only API interaction. Filtering against
     dietary restrictions, the ">=3 ingredients used" rule, ranking, and
     picking the top 3 all belong in logic_manager, NOT here.

Only function other layers should call:
    generate_recipes(user_input: dict) -> list[dict]

"""

import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# Gemini free tier
MODEL_NAME = "gemini-3.7-flash"
API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Keep retries low - each retry costs a request.
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 3          # backoff for generic failures (parse/API errors)
RATE_LIMIT_DELAY_SECONDS = 20    # longer backoff specifically for HTTP 429

MAX_OUTPUT_TOKENS = 1000         # kept low - schema enforcement means we don't
                                  # need extra tokens for the model to
                                  # "explain" the JSON shape.

THINKING_BUDGET = 0

LOG_FILE = "ai_manager_errors.log"

# Required fields
REQUIRED_RECIPE_FIELDS = {
    "recipe_name": str,
    "ingredients": list,
    "description": str,
    "seasonings": list,
    "instructions": list,
    "estimated_cooking_time_minutes": (int, float),
    "servings": (int, float),
}

# Makes it so the output is in this format
RECIPE_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "recipe_name": {"type": "STRING"},
            "ingredients": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "quantity": {"type": "STRING"},
                        "unit": {"type": "STRING"},
                    },
                    "required": ["name", "quantity", "unit"],
                },
            },
            "description": {"type": "STRING - explain how this recipe fits the requested cuisine and taste preference"},
            "seasonings": {"type": "ARRAY", "items": {"type": "STRING"}},
            "instructions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "estimated_cooking_time_minutes": {"type": "NUMBER"},
            "servings": {"type": "NUMBER"},
        },
        "required": [
            "recipe_name",
            "ingredients",
            "description",
            "seasonings",
            "instructions",
            "estimated_cooking_time_minutes",
            "servings",
        ],
    },
}

def build_prompt(user_input):
    """
    Turn the structured user_input dict (handed over by io_manager) into a
    prompt string. Kept short on purpose to save tokens.
    output enforced separately via RECIPE_RESPONSE_SCHEMA
 
    Expected keys in user_input:
        ingredients          : list[dict]  e.g. [{"name": "egg", "quantity": "2", "unit": "pcs"}]
        dietary_restrictions : list[str]
        cuisine               : str
        meal_type             : str
        taste_preference      : str
        max_cooking_time      : int (minutes)
        servings              : int
    """
    ingredients_text = ", ".join(
        f"{i.get('quantity', '')} {i.get('unit', '')} {i.get('name', '')}".strip()
        for i in user_input.get("ingredients", [])
    ) or "None specified"
 
    restrictions_text = ", ".join(user_input.get("dietary_restrictions", [])) or "None"
 
    prompt = f"""
Generate exactly 3 different recipes using these constraints.
 
Available ingredients: {ingredients_text}
Dietary restrictions / allergies / Halal requirements: {restrictions_text}
Cuisine preference: {user_input.get('cuisine', 'Any')}
Meal type: {user_input.get('meal_type', 'Any')}
Taste preference: {user_input.get('taste_preference', 'Any')}
Maximum cooking time: {user_input.get('max_cooking_time', 'No limit')} minutes
Servings: {user_input.get('servings', 1)}
 
Rules:
- Each recipe should use at least 3 of the listed ingredients where possible.
- Scale ingredient quantities to the requested servings.
- Avoid ingredients conflicting with the dietary restrictions.
- Cooking time must not exceed the stated maximum.
- Recipes must genuinely match the stated cuisine (authentic style, not just a Western dish with a foreign-sounding name).
- Keep descriptions and instructions concise.
"""
    return prompt.strip()



if __name__ == "__main__":
    print("ai_manager loaded successfully.")
    print(f"Model: {MODEL_NAME}")
    print(f"Required recipe fields: {list(REQUIRED_RECIPE_FIELDS.keys())}")

    print("\n--- build_prompt() test ---")
    sample_input = {
        "ingredients": [
            {"name": "egg", "quantity": "3", "unit": "pcs"},
            {"name": "spinach", "quantity": "1", "unit": "cup"},
            {"name": "cheddar cheese", "quantity": "50", "unit": "g"},
        ],
        "dietary_restrictions": ["No pork"],
        "cuisine": "Western",
        "meal_type": "Breakfast",
        "taste_preference": "Savoury",
        "max_cooking_time": 20,
        "servings": 2,
    }
    print(build_prompt(sample_input))

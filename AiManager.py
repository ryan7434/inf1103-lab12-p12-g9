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
            "description": {"type": "STRING"},
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


if __name__ == "__main__":
    print("ai_manager loaded successfully.")
    print(f"Model: {MODEL_NAME}")
    print(f"Required recipe fields: {list(REQUIRED_RECIPE_FIELDS.keys())}")
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
            "description": {
                "type": "STRING",
                "description": "Explain how this recipe fits the requested cuisine and taste preference",
            },
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


def call_ai_api(prompt):
    """
    Send the prompt to the Gemini API and return the raw text response.
 
    Returns:
        str  - the raw text response on success
        None - on any failure. Never raises, so callers can't crash.
        "RATE_LIMITED" - for HTTP 429 responses, so callers can implement a longer backoff if desired.
    """
    if not API_KEY:  #check the api key is set, if not log error and return None
        _log_error("No API key configured (GEMINI_API_KEY env var not set).")
        return None
 
    url = API_URL_TEMPLATE.format(model=MODEL_NAME) + "?" + urllib.parse.urlencode({"key": API_KEY})
 
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], #holds the prompt
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,  #limit the output tokens to avoid excessive cost and ensure schema compliance
            "responseMimeType": "application/json", #sets the response type to JSON so we can parse it easily
            "responseSchema": RECIPE_RESPONSE_SCHEMA, #sets the schema for the response to be in the format we want
            "thinkingConfig": {"thinkingBudget": THINKING_BUDGET}, #sets the thinking budget to 0 to avoid unnecessary cost and ensure the model doesn't spend time "thinking" about the response
        },  #python dict that holds the generation config for the API call
    }
    data = json.dumps(payload).encode("utf-8") #converts the python dict to a JSON string and then encodes it to bytes for the API call
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json"},
        method="POST",
    )   #request object that holds where to send the request, what body/data to send, what headers to include, and what method to use (POST)
 
    try:    
        with urllib.request.urlopen(request, timeout=30) as response:   #urlopen() sends the request to the API and waits for a response, with a timeout of 30 seconds
            response_body = json.loads(response.read().decode("utf-8"))   #reads the response body, decodes it from bytes to a string and then json.loads() parses the string into a python dict
            candidates = response_body.get("candidates", [])  #get candidates from the response body, which is a list of possible responses from the model
            if not candidates:
                _log_error("Gemini response had no candidates.") #log an error if there are no candidates in the response and return None
                return None
            parts = candidates[0].get("content", {}).get("parts", []) #get the content and parts from the canditates
            text_parts = [p.get("text", "") for p in parts] #take the text from each part and put it in a list
            return "".join(text_parts).strip() #join the text from each part into a single string
    #exception handling so the program doesn't crash if the API call fails or the response is malformed
    except urllib.error.HTTPError as e:    #HTTPError is raised when the server returns an error response (4xx or 5xx)
        error_body = " "    #initialize error_body to an empty string in case the body fails for any reason
        try:
            error_body = e.read().decode("utf-8")   #read the body of the error response and decode it from bytes to a string
        except (OSError, UnicodeDecodeError):
            pass
        if e.code == 429:   #HTTP 429 is the "Too Many Requests" error, which indicates that the client has sent too many requests in a given amount of time and is being rate limited
            _log_error("Gemini rate limit hit (HTTP 429).")
            return "RATE_LIMITED"   #return a specific value to indicate the rate limit was hit
        _log_error(f"HTTPError calling Gemini API: {e.code} {e.reason} | body: {error_body}")  #log the error code, reason, and body of the error response
        return None
    except urllib.error.URLError as e:  #URLError is raised when there is a networking failure
        _log_error(f"URLError calling Gemini API: {e.reason}")
        return None
    except (TimeoutError, json.JSONDecodeError, OSError) as e:  #Other errors are raised when there is a timeout, the response is not valid JSON, or there is an OS error
        _log_error(f"Error calling/parsing Gemini API transport: {e}")
        return None


def _log_error(message):    #the first underscore in the function name indicates that this function is intended to be private and not used outside of this file
    """Append a timestamped line to the log file. Never raises."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file: #open the log file in append mode, so we don't overwrite previous logs
            log_file.write(f"[{datetime.now().isoformat()}] {message}\n")
    except OSError:
        pass
    print(f"[ai_manager] {message}")



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
    test_prompt = build_prompt(sample_input)
    print(test_prompt)
 
    print("\n--- call_ai_api() test ---")
    if not API_KEY:
        print("GEMINI_API_KEY not set - skipping live API test.")
    else:
        print("Calling Gemini API ...")
        result = call_ai_api(test_prompt)
        if result == "RATE_LIMITED":
            print("Hit rate limit - try again in a minute.")
        elif result is None:
            print("API call failed - check ai_manager_errors.log for details.")
        else:
            print("Raw response:")
            print(result)


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

MAX_OUTPUT_TOKENS = 1800         # kept low - schema enforcement means we don't
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
Generate exactly 5 different recipes using these constraints.
 
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


def parse_ai_response(raw_text):
    """
    Parse raw_text as JSON
    Returns a list of recipe dicts, or None if parsing fails
    checks if the overall response is a list, if not it checks if it is a dict and wraps it in a list, if not it logs an error and returns None
    """
    if not raw_text:
        return None
 
    cleaned = raw_text.strip() 
    if cleaned.startswith("```"):   #checks if it begins witha  markdown fence
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]   #removes the "json" from the beginning of the string if it is present
        cleaned = cleaned.strip()
 
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        _log_error(f"JSON decode failed: {e} | raw (first 200 chars): {cleaned[:200]}")
        return None
 
    if isinstance(parsed, dict):    #if the parsed object is a dict, wrap it in a list
        parsed = [parsed]
 
    if not isinstance(parsed, list):
        _log_error("Parsed AI response was neither a list nor a dict.")
        return None
 
    return parsed


def validate_recipe_schema(recipe):
    """
    Check a single recipe dict has all required fields with the right
    rough types.
    Purely structural - does not check for anything specific
    checks if specific items are a dict
    """
    if not isinstance(recipe, dict):    #check if the recipe is a dict, if not return False
        return False
 
    for field, expected_type in REQUIRED_RECIPE_FIELDS.items(): #check if each required field is present in the recipe and if it is of the expected type, if not return False
        if field not in recipe:
            return False
        if not isinstance(recipe[field], expected_type):
            return False
 
    if not recipe["ingredients"]:   #check if the ingredients list is empty, if it is return False
        return False
    for ingredient in recipe["ingredients"]:    #check if each ingredient is a dict and has a "name" key, if not return False
        if not isinstance(ingredient, dict) or "name" not in ingredient:
            return False
 
    if not recipe["instructions"]:  #check if the instructions list is empty, if it is return False
        return False
 
    return True


def generate_recipes(user_input):
    """
    Main entry point called. only function other layers should call
 
    Chains together: build_prompt -> call_ai_api -> parse_ai_response ->
    validate_recipe_schema, with retries on failure and a longer backoff
    specifically for rate limiting.
 
    Returns a list of schema-valid recipe dicts. not yet filtered or
    ranked against business rules
 
    Returns an empty list (never raises) if the AI could not produce
    valid output after all retries, or if the API failed entirely. An
    empty list is a legitimate, expected outcome the other layers should handle
    """
    prompt = build_prompt(user_input)   
 
    for attempt in range(1, MAX_RETRIES + 1):   #loop through the number of retries, should be 2 attempts total
        raw_response = call_ai_api(prompt)
 
        if raw_response is None:    #log an error if the API call failed and sleep for a few seconds before retrying
            _log_error(f"Attempt {attempt}/{MAX_RETRIES}: API call failed.")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
 
        if raw_response == "RATE_LIMITED":  #log an error if the API call was rate limited and sleep for a longer period of time before retrying
            _log_error(f"Attempt {attempt}/{MAX_RETRIES}: backing off for rate limit.")
            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            continue
 
        recipes = parse_ai_response(raw_response)
        if recipes is None: #log an error if the response was not valid JSON and sleep for a few seconds before retrying
            _log_error(f"Attempt {attempt}/{MAX_RETRIES}: response was not valid JSON.")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
 
        valid_recipes = [r for r in recipes if validate_recipe_schema(r)]   #filter the list of recipes to only include those that pass schema validation
 
        if valid_recipes:
            return valid_recipes
 
        _log_error( #log an error if the response was valid JSON but none of the recipes passed schema validation and sleep for a few seconds before retrying
            f"Attempt {attempt}/{MAX_RETRIES}: JSON parsed but no recipe "
            f"passed schema validation."
        )
        time.sleep(RETRY_DELAY_SECONDS)
 
    _log_error("All retries exhausted - returning empty recipe list.")  #log an error if all retries have been exhausted and return an empty list
    return []


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
 
    print("\n--- generate_recipes() end-to-end test ---")
    if not API_KEY:
        print("GEMINI_API_KEY not set - skipping live API test.")
        print("(This is expected/fine if you're just checking syntax right now.)")
    else:
        print("Calling Gemini API via generate_recipes() (uses your free-tier quota,")
        print("possibly more than once if a retry is triggered)...")
        recipes = generate_recipes(sample_input)
        if not recipes:
            print("Got an empty list - check ai_manager_errors.log for what went wrong.")
        else:
            print(f"Got {len(recipes)} valid recipe(s):")
            for recipe in recipes:
                print(f"  - {recipe['recipe_name']} ({recipe['estimated_cooking_time_minutes']} min)")
 
    print("\n--- parse_ai_response() offline test (no API needed) ---")
    fake_clean_json = '[{"recipe_name": "Test Recipe", "ingredients": []}]' #valid JSON string
    fake_fenced_json = '```json\n[{"recipe_name": "Fenced Recipe"}]\n```'   #valid JSON string with markdown fences
    fake_garbage = "not json at all {broken"    #invalid JSON string
    print("clean JSON  ->", parse_ai_response(fake_clean_json)) #parse the valid JSON string and print the result
    print("fenced JSON ->", parse_ai_response(fake_fenced_json))    #parse the valid JSON string with markdown fences and print the result
    print("garbage     ->", parse_ai_response(fake_garbage))    #parse the invalid JSON string and calls _log_error
 
    print("\n--- validate_recipe_schema() offline test (no API needed) ---")
    fake_good_recipe = {    #a valid recipe dict with all required fields and correct types
        "recipe_name": "Spinach Cheddar Omelette",
        "ingredients": [{"name": "egg", "quantity": "6", "unit": "pcs"}],
        "description": "A savoury Western breakfast with no pork.",
        "seasonings": ["salt", "pepper"],
        "instructions": ["Whisk eggs.", "Cook in pan with spinach and cheese."],
        "estimated_cooking_time_minutes": 15,
        "servings": 2,
    }
    fake_missing_fields = {"recipe_name": "Missing everything else"}    #a recipe dict that is missing all required fields except for "recipe_name"
    fake_empty_ingredients = {**fake_good_recipe, "ingredients": []}    #a recipe dict that has an empty ingredients list
    fake_wrong_type = {**fake_good_recipe, "servings": "two"}   #a recipe dict that has the wrong type for the "servings" field (string instead of int/float)
    print("good recipe              ->", validate_recipe_schema(fake_good_recipe))
    print("missing fields           ->", validate_recipe_schema(fake_missing_fields))
    print("empty ingredients list   ->", validate_recipe_schema(fake_empty_ingredients))
    print("wrong type (servings)    ->", validate_recipe_schema(fake_wrong_type))
    print("not even a dict          ->", validate_recipe_schema("just a string"))

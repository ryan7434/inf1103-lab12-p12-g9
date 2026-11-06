"""
Only function other layers should call:
    generate_recipes(user_input: dict) -> list[dict]

"""

from abc import ABC, abstractmethod     #abstract base class for AIProvider
import os
import json
import time
from typing import Any, Callable
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

MAX_OUTPUT_TOKENS = 3500        # kept low - schema enforcement means we don't
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
    "is_breakfast": bool,
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
                "description": (
                    "Explain how this recipe fits the requested cuisine and taste preference"
                ),
            },
            "seasonings": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "instructions": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "estimated_cooking_time_minutes": {"type": "NUMBER"},
            "servings": {"type": "NUMBER"},
            "is_breakfast": {
                "type": "BOOLEAN",
                "description": (
                    "True if this recipe is suitable for breakfast, false otherwise"
                ),
            },
        },
        "required": [
            "recipe_name",
            "ingredients",
            "description",
            "seasonings",
            "instructions",
            "estimated_cooking_time_minutes",
            "servings",
            "is_breakfast",
        ],
    },
}

class AIError(Exception):
    """Base class for every failure the AI layer can report.

    Each subclass says whether retrying can help and how long to wait, so the
    retry loop never needs to check which kind of error it received.
    """

    retryable: bool = True
    retry_delay_seconds: float = 3

class AIConfigurationError(AIError):
    """The AI layer is not set up (for example, no API key). Retrying cannot help."""

    retryable = False
    retry_delay_seconds = 0

class AITransportError(AIError):
    """The request failed: network error, timeout or an HTTP error status."""

class AIRateLimitError(AITransportError):
    """The provider said we are sending too many requests (HTTP 429)."""

    retry_delay_seconds = 20


class AIResponseError(AIError):
    """A reply arrived but cannot be used: empty, not JSON, wrong shape or no valid recipes."""

class ErrorLogger:
    """Appends timestamped lines to a log file and echoes them to the terminal.

    Logging must never be the reason the app crashes, so file errors are ignored.
    """

    def __init__(self, log_file: str = "ai_manager_errors.log", prefix: str = "ai_manager") -> None:
        self._log_file = log_file
        self._prefix = prefix

    @property
    def log_file(self) -> str:
        return self._log_file

    def log(self, message: str) -> None:
        try:
            with open(self._log_file, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{datetime.now().isoformat()}] {message}\n")
        except OSError:
            pass
        print(f"[{self._prefix}] {message}")

class AIProvider(ABC):
    """Contract for anything that can turn a prompt into the model's raw text reply."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the raw text reply, or raise an AIError subclass. Never return None."""

class GeminiProvider(AIProvider):
    """AIProvider backed by the Gemini REST API (standard library only)."""

    DEFAULT_MODEL = "gemini-3.7-flash"
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str,
        response_schema: dict,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 90,
        max_output_tokens: int = 3500,
        thinking_budget: int = 0,
    ) -> None:
        self.__api_key = api_key  # private: never logged, never exposed as an attribute
        self._response_schema = response_schema
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._thinking_budget = thinking_budget

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        if not self.__api_key:
            raise AIConfigurationError("No API key configured (GEMINI_API_KEY env var not set).")
        body = self._post(self._build_request(prompt))
        return self._extract_text(body)

    def _build_request(self, prompt: str) -> urllib.request.Request:
        url = (
            self.API_URL_TEMPLATE.format(model=self._model)
            + "?"
            + urllib.parse.urlencode({"key": self.__api_key})
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self._max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": self._response_schema,
                "thinkingConfig": {"thinkingBudget": self._thinking_budget},
            },
        }
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )

    def _post(self, request: urllib.request.Request) -> Any:
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429:
                raise AIRateLimitError("Gemini rate limit hit (HTTP 429).") from error
            raise AITransportError(
                f"HTTPError calling Gemini API: {error.code} {error.reason} "
                f"| body: {self._read_error_body(error)}"
            ) from error
        except urllib.error.URLError as error:
            raise AITransportError(f"URLError calling Gemini API: {error.reason}") from error
        except (TimeoutError, json.JSONDecodeError, OSError) as error:
            raise AITransportError(f"Error calling/parsing Gemini API transport: {error}") from error

    @staticmethod
    def _read_error_body(error: urllib.error.HTTPError) -> str:
        try:
            return error.read().decode("utf-8")
        except (OSError, ValueError, AttributeError):
            return " "

    @staticmethod
    def _extract_text(body: Any) -> str:
        try:
            candidates = body.get("candidates", [])
            if not candidates:
                raise AIResponseError("Gemini response had no candidates.")
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts).strip()
        except (AttributeError, TypeError) as error:
            raise AIResponseError("Gemini response had an unexpected structure.") from error


class RecipePromptBuilder:
    """Turns the user's request (a dict from the IO layer) into the prompt text."""

    def build(self, user_input: dict) -> str:
        ingredients_text = self._format_ingredients(user_input.get("ingredients", []))
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

Ingredient quantity rules:
- Ingredient quantities must be positive numbers or fractions.
- Keep quantity and unit separate.
- For ingredients listed by the user, use the exact unit supplied
  for that ingredient, including custom units. Do not convert it
  or change its spelling.
- For additional ingredients, use these units:
  g, kg, ml, L, tbsp, tsp, pieces, clove, slice.
- Do not use vague quantities such as "a pinch", "a handful" in structured ingredient quantity fields.

Rules:
- Each recipe should use at least 3 of the listed ingredients where possible.
- Scale ingredient quantities to the requested servings.
- Avoid ingredients conflicting with the dietary restrictions.
- Cooking time must not exceed the stated maximum.
- Try to match the requested cuisine where possible, but allow other cuisines if needed. If the cuisine is any, any cuisine is acceptable.
- Keep descriptions and instructions concise.
- Set is_breakfast to true only if the actual dish is normally suitable for breakfast in the requested cuisine. Do not set it to true merely because the requested meal type is Breakfast.
"""
        return prompt.strip()

    @staticmethod
    def _format_ingredients(ingredients: list) -> str:
        return ", ".join(
            f"{i.get('quantity', '')} {i.get('unit', '')} {i.get('name', '')}".strip()
            for i in ingredients
        ) or "None specified"

class ResponseParser:
    """Turns the provider's raw text into a list of dicts, or raises AIResponseError."""

    def parse(self, raw_text: str) -> list:
        if not raw_text or not raw_text.strip():
            raise AIResponseError("AI response was empty.")

        cleaned = self._strip_markdown_fence(raw_text.strip())
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise AIResponseError(
                f"JSON decode failed: {error} | raw (first 200 chars): {cleaned[:200]}"
            ) from error

        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise AIResponseError("Parsed AI response was neither a list nor a dict.")
        return parsed

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        return text


class ResponseValidator(ABC):
    """Abstract base for checking AI output.

    filter_valid() is shared behaviour; each subclass supplies its own is_valid().
    """

    def filter_valid(self, items: list) -> list:
        return [item for item in items if self.is_valid(item)]

    @abstractmethod
    def is_valid(self, item: Any) -> bool:
        """Return True if one item has the structure this validator requires."""


class RecipeValidator(ResponseValidator):
    """Structural check for one recipe dict (fields, types, non-empty values)."""

    REQUIRED_FIELDS = {
        "recipe_name": str,
        "ingredients": list,
        "description": str,
        "seasonings": list,
        "instructions": list,
        "estimated_cooking_time_minutes": (int, float),
        "servings": (int, float),
        "is_breakfast": bool,
    }
    INGREDIENT_FIELDS = ("name", "quantity", "unit")

    def is_valid(self, recipe: Any) -> bool:
        return (
            isinstance(recipe, dict)
            and self._has_required_fields(recipe)
            and self._ingredients_are_valid(recipe["ingredients"])
            and self._text_items_are_valid(recipe["instructions"], allow_empty_list=False)
            and self._text_items_are_valid(recipe["seasonings"], allow_empty_list=True)
        )

    def _has_required_fields(self, recipe: dict) -> bool:
        for field, expected in self.REQUIRED_FIELDS.items():
            if field not in recipe:
                return False
            expected_types = expected if isinstance(expected, tuple) else (expected,)
            value = recipe[field]
            # bool is a subclass of int, so True would otherwise pass as a number
            if isinstance(value, bool) and bool not in expected_types:
                return False
            if not isinstance(value, expected_types):
                return False
        return True

    def _ingredients_are_valid(self, ingredients: list) -> bool:
        if not ingredients:
            return False
        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                return False
            for field in self.INGREDIENT_FIELDS:
                value = ingredient.get(field)
                if not isinstance(value, str) or not value.strip():
                    return False
        return True

    @staticmethod
    def _text_items_are_valid(items: list, allow_empty_list: bool) -> bool:
        if not items:
            return allow_empty_list
        return all(isinstance(item, str) and item.strip() for item in items)


class AiManager:
    """Coordinates the AI pipeline and handles failure without ever raising.

    The prompt builder, parser and validator are created here and belong to this object.
    """

    def __init__(
        self,
        provider: AIProvider,
        logger: ErrorLogger,
        max_attempts: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._provider = provider
        self._logger = logger
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._prompt_builder = RecipePromptBuilder()
        self._parser = ResponseParser()
        self._validator = RecipeValidator()

    @classmethod
    def from_environment(cls) -> "AiManager":
        """Build the default manager: Gemini, key from GEMINI_API_KEY, errors to the log file."""
        provider = GeminiProvider(
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            response_schema=RECIPE_RESPONSE_SCHEMA,
        )
        return cls(provider=provider, logger=ErrorLogger())

    def generate_recipes(self, user_input: dict) -> list:
        """Return schema-valid recipe dicts, or an empty list if the AI could not deliver."""
        prompt = self._prompt_builder.build(user_input)

        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._request_valid_recipes(prompt)
            except AIError as error:
                will_retry = error.retryable and attempt < self._max_attempts
                suffix = f" Retrying in {error.retry_delay_seconds:g}s." if will_retry else ""
                self._logger.log(f"Attempt {attempt}/{self._max_attempts} failed: {error}{suffix}")
                if not error.retryable:
                    return []
                if will_retry:
                    self._sleep(error.retry_delay_seconds)

        self._logger.log("All retries exhausted - returning empty recipe list.")
        return []

    def is_valid_recipe(self, recipe: Any) -> bool:
        """Lets other layers re-check a recipe without knowing about the validator."""
        return self._validator.is_valid(recipe)

    def _request_valid_recipes(self, prompt: str) -> list:
        raw_text = self._provider.generate(prompt)
        recipes = self._validator.filter_valid(self._parser.parse(raw_text))
        if not recipes:
            raise AIResponseError("JSON parsed but no recipe passed schema validation.")
        return recipes
    
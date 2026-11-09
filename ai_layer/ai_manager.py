import os
import time
from typing import Any, Callable

from .ai_error import AIError
from .ai_provider import AIProvider
from .ai_response_error import AIResponseError
from .error_logger import ErrorLogger
from .gemini_provider import GeminiProvider
from .recipe_prompt_builder import RecipePromptBuilder
from .recipe_schema import RECIPE_RESPONSE_SCHEMA
from .recipe_validator import RecipeValidator
from .response_parser import ResponseParser


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
    
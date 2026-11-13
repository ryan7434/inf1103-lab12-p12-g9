import os
import time
from typing import Any, Callable

from ai_layer import (
    AIError, AIProvider, AIResponseError, ErrorLogger, FallbackProvider,
    GeminiProvider, RecipePromptBuilder, RecipeValidator, ResponseParser,
)
from ai_layer.recipe_schema import RECIPE_RESPONSE_SCHEMA

# Pipeline: build prompt -> ask the AI -> parse the text -> validate recipes,
# retrying when something goes wrong. The rest of the app only talks to this class.
class AiManager:
    """Coordinates the AI pipeline and handles failure without ever raising.

    The prompt builder, parser and validator are created here and belong to this object.
    """

    def __init__(
        self,
        provider: AIProvider,   # the AI to ask (Gemini, or a fake one in tests)
        logger: ErrorLogger,    # where failures get recorded
        max_attempts: int = 3,  # total tries, including the first one
        sleep: Callable[[float], None] = time.sleep,    # wait function; tests replace it so they run instantly
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        # Objects passed in from outside (they can be shared and reused elsewhere).
        self._provider = provider
        self._logger = logger
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._prompt_builder = RecipePromptBuilder()
        self._parser = ResponseParser()
        self._validator = RecipeValidator()

    # Convenience builder for the normal app setup: real Gemini, API key read
    # from the GEMINI_API_KEY environment variable, errors logged to the default file.
    # If the main model is busy, the next model in the list is tried (free-tier
    # limits are per model). Three attempts keeps the number of requests small.
    @classmethod
    def from_environment(cls) -> "AiManager":
        """Build the default manager: Gemini (with fallback models), key from GEMINI_API_KEY."""
        logger = ErrorLogger()
        api_key = os.environ.get("GEMINI_API_KEY", "")
        models = (GeminiProvider.DEFAULT_MODEL, *GeminiProvider.FALLBACK_MODELS)
        provider = FallbackProvider(
            [
                GeminiProvider(
                    api_key=api_key,
                    response_schema=RECIPE_RESPONSE_SCHEMA,
                    model=model,
                )
                for model in models
            ],
            logger=logger,
        )
        return cls(provider=provider, logger=logger, max_attempts=3)

    # Main method used by the rest of the app. It never raises an error:
    # on failure it returns an empty list instead.
    def generate_recipes(self, user_input: dict) -> list:
        """Return schema-valid recipe dicts, or an empty list if the AI could not deliver."""
        prompt = self._prompt_builder.build(user_input)

        # Try up to max_attempts times.
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._request_valid_recipes(prompt)   # success: return straight away
            except AIError as error:
                # Retry only if this error type allows it AND attempts remain.
                will_retry = error.retryable and attempt < self._max_attempts
                suffix = f" Retrying in {error.retry_delay_seconds:g}s." if will_retry else ""
                self._logger.log(f"Attempt {attempt}/{self._max_attempts} failed: {error}{suffix}")
                if not error.retryable:
                    return []   # retrying can't help (e.g. missing API key), so stop now
                if will_retry:
                    self._sleep(error.retry_delay_seconds)  # wait before the next try

        # Reached only when every attempt failed.
        self._logger.log("All retries exhausted - returning empty recipe list.")
        return []

    def is_valid_recipe(self, recipe: Any) -> bool:
        """Lets other layers re-check a recipe without knowing about the validator."""
        return self._validator.is_valid(recipe)

    # One full attempt: ask the AI, parse the reply, keep only valid recipes.
    # Raises AIResponseError if nothing usable came back, which triggers a retry.
    def _request_valid_recipes(self, prompt: str) -> list:
        raw_text = self._provider.generate(prompt)
        recipes = self._validator.filter_valid(self._parser.parse(raw_text))
        if not recipes:
            raise AIResponseError("JSON parsed but no recipe passed schema validation.")
        return recipes
from typing import Sequence

from .ai_overloaded_error import AIOverloadedError
from .ai_provider import AIProvider
from .ai_rate_limit_error import AIRateLimitError

"""
Where the error starts: gemini_provider.py
    1. GeminiProvider._post() sends the HTTP request to Google.
    2. When the model is busy, Google replies with HTTP status 503 (“high demand”).
    3. Pythons urllib turns that into an HTTPError with error.code == 503.
    4. The new check catches it and raises AIOverloadedError("Gemini model overloaded (HTTP 503).").

What happens next, step by step
    1. FallbackProvider catches it first. It sees an AIOverloadedError for model 1 and moves on to model 2 straight away, with no waiting. 
        It logs “AIOverloadedError from provider 1; trying the next one.”
    2. If model 2 works, its reply goes back up as normal. The manager never learns that model 1 was busy.
    3. If model 2 is also busy, FallbackProvider re-raises the last error, because no providers are left.
    4. AiManager.generate_recipes() catches it in its except AIError block. 
        It reads two properties from the error: retryable (True) and retry_delay_seconds (10, from ai_overloaded_error.py).
    5. It logs the failure and sleeps 10 seconds, then starts a new attempt. 
        That attempt tries model 1 again, then model 2. This repeats up to max_attempts=3.
    6. If all 3 attempts fail, it logs “All retries exhausted” and returns [].
        It never raises an exception, so the app shows “no recipes” instead of crashing.

 Example timeline when both models are busy:
    attempt 1: model 1 503 → model 2 503 → wait 10s
    attempt 2: model 1 503 → model 2 503 → wait 10s
    attempt 3: model 1 503 → model 2 503 → give up → []
"""

# An AIProvider made of other AIProviders. It asks the first one; if that model
# is busy or over its limit, it asks the next one. AiManager does not need to
# change, because it only ever sees one AIProvider.
class FallbackProvider(AIProvider):
    """Tries several providers in order and returns the first reply that works."""

    # Only these failures mean "another model might do better".
    # A missing API key (same key everywhere) or an unusable reply is not on the list.
    SWITCH_ON = (AIOverloadedError, AIRateLimitError)

    def __init__(self, providers: Sequence[AIProvider], logger=None) -> None:
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        self._providers = tuple(providers)  # in order of preference
        self._logger = logger               # optional: anything with a log(message) method

    # Read-only access to the providers, in the order they are tried.
    @property
    def providers(self) -> tuple:
        return self._providers

    def generate(self, prompt: str) -> str:
        last_error = None
        for position, provider in enumerate(self._providers):
            try:
                return provider.generate(prompt)
            except self.SWITCH_ON as error:
                last_error = error
                if self._logger is not None and position < len(self._providers) - 1:
                    self._logger.log(f"{type(error).__name__} from provider {position + 1}; trying the next one.")
        # Every provider was busy: let the manager decide how long to wait and retry.
        raise last_error
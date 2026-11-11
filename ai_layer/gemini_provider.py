import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .ai_configuration_error import AIConfigurationError
from .ai_provider import AIProvider
from .ai_rate_limit_error import AIRateLimitError
from .ai_response_error import AIResponseError
from .ai_transport_error import AITransportError

# The real AI provider: sends the prompt to Google's Gemini over the internet
# and returns the text it replies with. Uses only Python's standard library.
class GeminiProvider(AIProvider):
    """AIProvider backed by the Gemini REST API (standard library only)."""

    DEFAULT_MODEL = "gemini-3.8-flash"
    #{model} is filled in with the model name when the URL is built.
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str,
        response_schema: dict,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 90,  # give up on the request after this many seconds
        max_output_tokens: int = 3500,  # upper limit on the length of the AI's reply
        thinking_budget: int = 0,    # 0 turns off extra "thinking" to make replies faster
    ) -> None:
        self.__api_key = api_key  # private: never logged, never exposed as an attribute
        self._response_schema = response_schema
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._thinking_budget = thinking_budget

    # Read-only access to the model name.
    @property
    def model(self) -> str:
        return self._model

    # Main entry point: prompt in, raw reply text out.
    def generate(self, prompt: str) -> str:
        # Fail immediately if there is no key, because the request cannot succeed.
        if not self.__api_key:
            raise AIConfigurationError("No API key configured (GEMINI_API_KEY env var not set).")
        body = self._post(self._build_request(prompt))   # send the request, get the JSON reply
        return self._extract_text(body)     # pull the text out of that JSON

    # Builds the HTTP request: the URL (with the key), and the JSON body that
    # holds the prompt and the output settings.
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
                "responseMimeType": "application/json",  # ask for JSON, not free text
                "responseSchema": self._response_schema,    # force the recipe format
                "thinkingConfig": {"thinkingBudget": self._thinking_budget},
            },
        }
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )

    # Sends the request and converts every kind of failure into one of our own
    # error classes, so the manager only has to deal with AIError types.
    def _post(self, request: urllib.request.Request) -> Any:
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
              # HTTP 429 = too many requests, which needs a longer wait.
            if error.code == 429:
                raise AIRateLimitError("Gemini rate limit hit (HTTP 429).") from error
             # Any other HTTP error (400, 500...) includes the server's message for debugging.
            raise AITransportError(
                f"HTTPError calling Gemini API: {error.code} {error.reason} "
                f"| body: {self._read_error_body(error)}"
            ) from error
        except urllib.error.URLError as error:
            # Could not reach the server at all (no internet, bad address...).
            raise AITransportError(f"URLError calling Gemini API: {error.reason}") from error
        except (TimeoutError, json.JSONDecodeError, OSError) as error:
            # Timeout, a reply that isn't JSON, or another low-level network problem.
            raise AITransportError(f"Error calling/parsing Gemini API transport: {error}") from error

    # Tries to read the error message the server sent; returns a blank if it can't.
    @staticmethod
    def _read_error_body(error: urllib.error.HTTPError) -> str:
        try:
            return error.read().decode("utf-8")
        except (OSError, ValueError, AttributeError):
            return " "

    # Gets the reply text out of Gemini's JSON structure:
    # body -> candidates[0] -> content -> parts -> text
    @staticmethod
    def _extract_text(body: Any) -> str:
        try:
            candidates = body.get("candidates", [])
            if not candidates:
                raise AIResponseError("Gemini response had no candidates.")
            parts = candidates[0].get("content", {}).get("parts", [])
            # The reply can be split into several parts; join them into one string.
            return "".join(part.get("text", "") for part in parts).strip()
        except (AttributeError, TypeError) as error:
             # The JSON did not have the shape we expected.
            raise AIResponseError("Gemini response had an unexpected structure.") from error

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


class GeminiProvider(AIProvider):
    """AIProvider backed by the Gemini REST API (standard library only)."""

    DEFAULT_MODEL = "gemini-3.6-flash"
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

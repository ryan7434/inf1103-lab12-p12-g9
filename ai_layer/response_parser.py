import json

from .ai_response_error import AIResponseError


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

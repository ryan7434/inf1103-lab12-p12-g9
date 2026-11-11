import json

from .ai_response_error import AIResponseError

# Converts the AI's raw text reply into Python data (a list of dicts).
class ResponseParser:
    """Turns the provider's raw text into a list of dicts, or raises AIResponseError."""

    def parse(self, raw_text: str) -> list:
        # An empty or whitespace-only reply is unusable.
        if not raw_text or not raw_text.strip():
            raise AIResponseError("AI response was empty.")
        # Remove ```json ... ``` wrapping if the AI added it.
        cleaned = self._strip_markdown_fence(raw_text.strip())
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as error:
             # Include the first 200 characters so the log shows what went wrong.
            raise AIResponseError(
                f"JSON decode failed: {error} | raw (first 200 chars): {cleaned[:200]}"
            ) from error
        # If the AI returned one recipe instead of a list, wrap it in a list.
        if isinstance(parsed, dict):
            parsed = [parsed]
        # Anything else (a number, a string...) is not a recipe list.
        if not isinstance(parsed, list):
            raise AIResponseError("Parsed AI response was neither a list nor a dict.")
        return parsed

    # Some models wrap JSON in a markdown code block. This removes the
    # ``` marks and the optional "json" label so json.loads() can read it.
    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        return text

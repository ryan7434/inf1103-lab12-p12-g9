import json

from .ai_response_error import AIResponseError


class ResponseParser:
    """Turn provider text into a list, or raise AIResponseError."""

    # Application policy: characters, not bytes.
    MAX_RESPONSE_CHARACTERS = 200_000
    MAX_DIAGNOSTIC_CHARACTERS = 200
    MAX_PREVIEW_CHARACTERS = 200

    def parse(self, raw_text: str) -> list:
        if not isinstance(raw_text, str):
            raise AIResponseError("AI response must be a string.")

        # Check before stripping fences or attempting JSON decoding.
        if len(raw_text) > self.MAX_RESPONSE_CHARACTERS:
            raise AIResponseError(
                "AI response exceeded the "
                f"{self.MAX_RESPONSE_CHARACTERS}-character limit."
            )

        if not raw_text.strip():
            raise AIResponseError("AI response was empty.")
        cleaned = self._strip_markdown_fence(raw_text.strip())
        try:
            parsed = json.loads(cleaned)
        except (ValueError, RecursionError) as error:
            diagnostic = str(error)[:self.MAX_DIAGNOSTIC_CHARACTERS]
            preview = cleaned[:self.MAX_PREVIEW_CHARACTERS]
            raise AIResponseError(
                f"JSON decode failed: {diagnostic} "
                f"| raw preview: {preview}"
            ) from error

        # Preserve support for a single recipe object.
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise AIResponseError(
                "Parsed AI response was neither a list nor a dict."
            )
        return parsed

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        return text
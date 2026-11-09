from .ai_error import AIError


class AIConfigurationError(AIError):
    """The AI layer is not set up (for example, no API key). Retrying cannot help."""

    retryable = False
    retry_delay_seconds = 0

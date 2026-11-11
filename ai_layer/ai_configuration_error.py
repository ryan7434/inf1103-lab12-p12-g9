from .ai_error import AIError

# Raised when the AI layer is set up wrongly (e.g. the API key is missing).
# The user has to fix the setup, so trying again would just fail the same way.
class AIConfigurationError(AIError):
    """The AI layer is not set up (for example, no API key). Retrying cannot help."""

    retryable = False
    retry_delay_seconds = 0

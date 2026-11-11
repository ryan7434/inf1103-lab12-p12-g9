from .ai_error import AIError

# Raised when the request itself failed to reach Gemini or come back
# (network down, timeout, HTTP error code). Retryable with the default 3s delay
# inherited from AIError.
class AITransportError(AIError):
    """The request failed: network error, timeout or an HTTP error status."""

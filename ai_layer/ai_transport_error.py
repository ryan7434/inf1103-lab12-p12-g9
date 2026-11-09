from .ai_error import AIError


class AITransportError(AIError):
    """The request failed: network error, timeout or an HTTP error status."""

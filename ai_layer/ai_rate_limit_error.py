from .ai_transport_error import AITransportError


class AIRateLimitError(AITransportError):
    """The provider said we are sending too many requests (HTTP 429)."""

    retry_delay_seconds = 20

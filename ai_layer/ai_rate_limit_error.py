from .ai_transport_error import AITransportError

# A special kind of transport error: Gemini told us we are sending too many requests.
# It inherits from AITransportError, so code that handles transport errors handles this too.
class AIRateLimitError(AITransportError):
    """The provider said we are sending too many requests (HTTP 429)."""

    # Wait longer than usual so the rate limit has time to reset.
    retry_delay_seconds = 20

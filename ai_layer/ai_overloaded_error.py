from .ai_transport_error import AITransportError

# A special kind of transport error: Gemini told us the model is busy (HTTP 503,
# "high demand"). This is a capacity problem on Google's side, not a mistake in
# our request, so waiting a few seconds and trying again usually works.
# It inherits from AITransportError, so code that handles transport errors handles this too.
class AIOverloadedError(AITransportError):
    """The model is temporarily overloaded (HTTP 503). Retrying later usually works."""

    # Longer than the default 3 seconds, because busy periods last a while.
    retry_delay_seconds = 10
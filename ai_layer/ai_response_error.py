from .ai_error import AIError

# Raised when Gemini DID reply, but the reply is not usable.
# Retryable, because the model may give a better answer on the next try.
class AIResponseError(AIError):
    """A reply arrived but cannot be used: empty, not JSON, wrong shape or no valid recipes."""

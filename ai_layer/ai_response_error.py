from .ai_error import AIError


class AIResponseError(AIError):
    """A reply arrived but cannot be used: empty, not JSON, wrong shape or no valid recipes."""

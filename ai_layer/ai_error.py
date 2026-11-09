class AIError(Exception):
    """Base class for every failure the AI layer can report.

    Each subclass says whether retrying can help and how long to wait, so the
    retry loop never needs to check which kind of error it received.
    """

    retryable: bool = True
    retry_delay_seconds: float = 3

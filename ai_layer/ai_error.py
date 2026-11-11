# Having one parent class lets other code catch "any AI problem" with a single
# `except AIError`, instead of listing every specific error type.
class AIError(Exception):
    """Base class for every failure the AI layer can report.

    Each subclass says whether retrying can help and how long to wait, so the
    retry loop never needs to check which kind of error it received.
    """

    # Can the same request be tried again? Subclasses override this when retrying is pointless.
    retryable: bool = True
    # How many seconds to wait before the next attempt. Subclasses override for longer waits.
    retry_delay_seconds: float = 3

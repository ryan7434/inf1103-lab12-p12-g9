from dataclasses import dataclass
from status_logic_manager import Status


@dataclass
class EvaluationResult:
    """Final outcome returned to the application."""
    status: Status
    reason: str
    score: int
    warning: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "score": self.score,
            "warning": self.warning,
        }

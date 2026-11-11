from dataclasses import dataclass, field
from logic_layer.status_logic_manager import Status


@dataclass
class EvaluationResult:
    """Final outcome returned to the application."""
    status: Status
    reason: str
    score: int
    warning: str | None = None

    # Combined manual checks returned by the rules.
    manual_validation: list[dict] = field(default_factory=list)

    @property
    def validation_state(self):
        if self.status == Status.REJECT:
            return "rejected"

        if self.manual_validation:
            return "pending_manual_validation"

        return "automated_checks_passed"

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "score": self.score,
            "warning": self.warning,
            "manual_validation": self.manual_validation,
            "validation_state": self.validation_state,
        }
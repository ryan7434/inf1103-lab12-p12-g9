from dataclasses import dataclass

@dataclass
class RuleResult:
    """Outcome of one rule. passed=False is a hard failure (reject)."""
    passed: bool
    warning: str | None = None
    score: int = 0

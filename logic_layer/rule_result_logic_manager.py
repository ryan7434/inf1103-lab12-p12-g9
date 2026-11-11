from dataclasses import dataclass, field


@dataclass
class RuleResult:
    """Outcome of one rule. passed=False is a hard failure (reject)."""
    passed: bool
    warning: str | None = None
    score: int = 0

    #ingredients that need the user to check their contents
    manual_validation: list[dict] = field(default_factory=list)
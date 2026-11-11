from dataclasses import dataclass


@dataclass(frozen=True)
class DietaryCheck:
    """Maps a user restriction to the AI field that verifies it."""
    ai_field: str
    required_value: bool
    warning: str

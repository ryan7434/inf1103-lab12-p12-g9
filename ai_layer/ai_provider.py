from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Contract for anything that can turn a prompt into the model's raw text reply."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the raw text reply, or raise an AIError subclass. Never return None."""

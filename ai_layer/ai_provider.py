from abc import ABC, abstractmethod

# Abstract "contract" for any AI service. AiManager only knows about this class,
# so Gemini can later be swapped for another AI (or a fake one in tests)
# without changing the manager.

class AIProvider(ABC):
    """Contract for anything that can turn a prompt into the model's raw text reply."""

    # Every provider must implement this method, or Python refuses to create it.
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the raw text reply, or raise an AIError subclass. Never return None."""

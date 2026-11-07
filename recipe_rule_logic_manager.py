from abc import ABC, abstractmethod
from rule_result_logic_manager import RuleResult


class RecipeRule(ABC):
    """Interface for all recipe rules.

    Contract: evaluate() returns a RuleResult.
    """

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        pass

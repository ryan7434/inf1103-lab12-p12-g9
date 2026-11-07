from recipe_rule_logic_manager import RecipeRule
from rule_result_logic_manager import RuleResult

# breakfast preference scoring (soft preference, not a hard validation)
class BreakfastPreferenceRule(RecipeRule):

    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        matches = bool(user_preferences["breakfast_preferred"]) and bool(ai_response["is_breakfast"])
        return RuleResult(passed=True, score=1 if matches else 0)

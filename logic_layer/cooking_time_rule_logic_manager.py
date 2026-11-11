from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult


class CookingTimeRule(RecipeRule):

    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:

        max_time = user_preferences["maximum_cooking_time"]
        ai_time = ai_response["cooking_time_minutes"]

        if ai_time > max_time:
            return RuleResult(
                passed=False,
                warning=(
                    f"Recipe takes {ai_time} minutes, "
                    f"exceeding your {max_time}-minute limit."),
            )
        return RuleResult(passed=True)

from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult

# checks recipe uses at least 3 of the user's ingredient input
class MainIngredientRule(RecipeRule):

    def __init__(self, min_matches: int = 3):
        self.__min_matches = min_matches

    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        user_ingredient = {
            item["name"].strip().lower()
            for item in user_preferences["available_ingredients"]
        }
        ai_ingredient = {
            name.strip().lower()
            for name in ai_response["main_ingredients_used"]
        }

        match_count = len(user_ingredient & ai_ingredient)

        if match_count < self.__min_matches:
            return RuleResult(
                passed=False,
                warning=(f"Recipe uses only {match_count} of required ingredients. "
                         f"At least {self.__min_matches} are required."),
            )
        return RuleResult(passed=True)

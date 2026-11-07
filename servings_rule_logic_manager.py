from recipe_rule_logic_manager import RecipeRule
from rule_result_logic_manager import RuleResult

# checks recipe for max 5 servings
class ServingsRule(RecipeRule):

    def __init__(self, max_servings: int = 5):
        self.__max_servings = max_servings

    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        requested = user_preferences["servings"]
        actual = ai_response["servings"]

        if actual > self.__max_servings:
            return RuleResult(
                passed=False,
                warning=f"This recipe serves more than {self.__max_servings} people.",
            )

        if actual < requested:
            return RuleResult(
                passed=True,
                warning=(f"This recipe serves {actual} people, "
                         f"less than your requested {requested}. "
                         "Proceed only if you are okay with this."),
            )
        return RuleResult(passed=True)

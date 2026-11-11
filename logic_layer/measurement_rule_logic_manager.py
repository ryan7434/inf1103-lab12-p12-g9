from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult

class MeasurementRule(RecipeRule):

    # unit -> (dimension, factor to base unit); base units are g and ml
    CONVERSIONS = {
        "g": ("mass", 1),
        "kg": ("mass", 1000),
        "ml": ("volume", 1),
        "l": ("volume", 1000),
        "pieces": ("count", 1),
        "piece": ("count", 1),
    }

    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        # Lookup by ingredient name instead of a nested loop
        available = {
            item["name"].strip().lower(): item
            for item in user_preferences["available_ingredients"]
        }
        warnings = []

        for recipe_item in ai_response["ingredients"]:
            name = recipe_item["name"].strip().lower()
            user_item = available.get(name)
            if user_item is None:
                continue

            recipe_unit = recipe_item["unit"].strip().lower()
            user_unit = user_item["unit"].strip().lower()

            if recipe_unit not in self.CONVERSIONS or user_unit not in self.CONVERSIONS:
                continue

            recipe_dim, recipe_factor = self.CONVERSIONS[recipe_unit]
            user_dim, user_factor = self.CONVERSIONS[user_unit]

            if recipe_dim != user_dim:
                warnings.append(
                    f"Cannot compare {name}: recipe uses {recipe_unit} "
                    f"but you have {user_unit}."
                )
                continue

            if recipe_item["amount"] * recipe_factor > user_item["amount"] * user_factor:
                warnings.append(
                    f"Recipe requires {recipe_item['amount']} {recipe_unit} of {name}, "
                    f"but you have only {user_item['amount']} {user_unit}."
                )

        # Measurement problems are advisory, never a hard failure
        return RuleResult(passed=True, warning=" ".join(warnings) if warnings else None)

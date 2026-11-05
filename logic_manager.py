from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class Status(Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
 
 
@dataclass
class RuleResult:
    """Outcome of one rule. passed=False is a hard failure (reject)."""
    passed: bool
    warning: str | None = None
    score: int = 0
 
 
@dataclass
class EvaluationResult:
    """Final outcome returned to the rest of the application."""
    status: Status
    reason: str
    score: int
    warning: str | None = None
 
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "score": self.score,
            "warning": self.warning,
        }
 
 
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

#--------------------
# Rules
#--------------------

# maximum cooking time validation
class CookingTimeRule(RecipeRule):
 
    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        max_time = user_preferences["maximum_cooking_time"]
        ai_time = ai_response["cooking_time_minutes"]
 
        if ai_time > max_time:
            return RuleResult(
                passed=False,
                warning=(f"Recipe takes {ai_time} minutes, "
                         f"exceeding your {max_time}-minute limit."),
            )
        return RuleResult(passed=True)

# dietary restrictions validation
@dataclass(frozen=True)
class DietaryCheck:
    """Maps a user restriction to the AI field that verifies it."""
    ai_field: str
    required_value: bool
    warning: str
 
 
DEFAULT_DIETARY_CHECKS = {
    "halal": DietaryCheck("halal_suitable", True, "The recipe may not be halal."),
    "no peanuts": DietaryCheck("contains_peanuts", False, "The recipe contains peanuts."),
}

class DietaryRestrictionRule(RecipeRule):
 
    def __init__(self, checks: dict[str, DietaryCheck] | None = None):
        # New restrictions are added as data, not by editing an if/elif chain.
        self.__checks = checks if checks is not None else dict(DEFAULT_DIETARY_CHECKS)
 
    @staticmethod
    def _to_bool(value) -> bool:
        # Supports both JSON booleans and string values
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() == "true"
 
    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        dietary_info = ai_response["dietary_information"]
        failures = []
        unverified = []
 
        for restriction in user_preferences["dietary_restrictions"]:
            key = restriction.strip().lower()
            check = self.__checks.get(key)
 
            if check is None:
                unverified.append(restriction)
                continue
 
            actual = self._to_bool(dietary_info[check.ai_field])
            if actual != check.required_value:
                failures.append(check.warning)
 
        warnings = list(failures)
        if unverified:
            warnings.append(
                "Could not verify these restrictions: "
                + ", ".join(unverified) + "."
            )
 
        # Unverifiable restrictions warn but do not reject.
        return RuleResult(
            passed=not failures,
            warning=" ".join(warnings) if warnings else None,
        )


# breakfast preference scoring (soft preference, not a hard validation)
class BreakfastPreferenceRule(RecipeRule):
 
    def evaluate(self, user_preferences: dict, ai_response: dict) -> RuleResult:
        matches = bool(user_preferences["breakfast_preferred"]) and bool(ai_response["is_breakfast"])
        return RuleResult(passed=True, score=1 if matches else 0)

# checks recipe uses at least 3 of the user's ingredient input
def check_main_ingredient(user_preference, ai_response):
    user_ingredient = user_preference["available_ingredients"]
    ai_ingredient = ai_response["main_ingredients_used"]

    match_count = 0

    for ingredient in user_ingredient:
          ingredient_name = ingredient["name"]
          if ingredient_name.lower() in [
              item.lower() for item in ai_ingredient
    ]:
            match_count += 1

    if match_count >= 3:
        return True

    return False

# checks recipe for max 5 servings
def check_max_servings(user_preference, ai_response):
    user_servings = user_preference["servings"]
    ai_servings = ai_response["servings"]

    if ai_servings > 5:
        return {
            "passed": False,
            "warning": f"This recipe serves more than 5 servings."
        }

    if ai_servings < user_servings:
        return {
            "passed": True,
            "warning": f"This recipe can only serve {ai_servings} servings. Proceed only if you are okay with this."
        }

    return {
        "passed": True,
        "warning": None
    }

def check_measurements(user_preference, ai_response):
    warnings = []

    user_ingredients = user_preference["available_ingredients"]

    for recipe_item in ai_response["ingredients"]:
        recipe_name = recipe_item["name"].lower()
        recipe_amount = recipe_item["amount"]
        recipe_unit = recipe_item["unit"].lower()

        for user_item in user_ingredients:
            user_name = user_item["name"].lower()

            if recipe_name == user_name:
                user_amount = user_item["amount"]
                user_unit = user_item["unit"].lower()

                # Only compare amounts when the units are the same
                if recipe_unit == user_unit:
                    if recipe_amount > user_amount:
                        warnings.append(
                            f"The recipe requires {recipe_amount} {recipe_unit} "
                            f"of {recipe_name}, but you only have "
                            f"{user_amount} {user_unit}."
                        )

                break

    return {
        "passed": True,
        "warning": "; ".join(warnings) if warnings else None
    }

def evaluate_recipe(user_preferences, ai_response):

    cooking_time_ok = validate_cooking_time(
        user_preferences,
        ai_response
    )
    dietary_ok = validate_dietary_restriction(
        user_preferences,
        ai_response
    )

    ingredients_ok = check_main_ingredient(
        user_preferences,
        ai_response
    )

    servings_ok = check_max_servings(
        user_preferences,
        ai_response
    )

    measurements_ok = check_measurements(
        user_preferences, 
        ai_response
    )

    #A dict is always truthy even when passed=False, so a recipe that actually failed the cooking-time or 
    # halal/peanut dietary check could still be returned as "ACCEPT" if the other checks passed
    if (
            ingredients_ok
            and servings_ok["passed"]
            and measurements_ok["passed"]
            and cooking_time_ok["passed"]
            and dietary_ok["passed"]
        ):
            return {
            "status": "ACCEPT",
            "reason": "Recipe meets all requirements.",
            "warning": servings_ok["warning"] or measurements_ok["warning"] or cooking_time_ok["warning"] or dietary_ok["warning"]
        }

    return {
        "status": "REJECT",
        "reason": "Recipe does not meet all requirements.",
        "warning": servings_ok["warning"] or measurements_ok["warning"] or cooking_time_ok["warning"] or dietary_ok["warning"]
    }


if __name__ == "__main__":
    with open("test_script_user_input.json", "r") as f:
        user_response = json.load(f)
    with open("test_script_AI.json", "r") as f:
        ai_response = json.load(f)

    result = evaluate_recipe(user_response, ai_response)
    print(result)


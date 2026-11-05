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

class MeasurementRule(RecipeRule):
 
    # unit -> (dimension, factor to base unit); base units are g and ml
    CONVERSIONS = {
        "g": ("mass", 1),
        "kg": ("mass", 1000),
        "ml": ("volume", 1),
        "l": ("volume", 1000),
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


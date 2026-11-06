from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import re
from dictionary import INGREDIENT_ALLERGENS, ALLERGEN_RESTRICTIONS

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

    def __init__(self):
    self.__checks = DEFAULT_DIETARY_CHECKS

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]

        return bool(value)

    def _find_allergen_matches(self, ingredient, allergen):
        matches = []

        for key, allergens in INGREDIENT_ALLERGENS.items():
            
            # Check whether this ingredient is associated
            # with the allergen being searched for.
            if allergen in allergens:

                # Match the ingredient name or phrase.
                if re.search(
                    rf"\b{re.escape(key)}\b",
                    ingredient
                ):
                    matches.append(key)
    
    return matches

    def evaluate(self, user_preferences, ai_response):

        dietary_info = ai_response["dietary_information"]

        failures = []
        unverified = []

        # Extract the recipe ingredient names.
        recipe_ingredients = [
            item["name"].strip().lower()
            for item in ai_response["ingredients"]
        ]

        # Check each dietary restriction selected by the user.
        for restriction in user_preferences["dietary_restrictions"]:
            key = restriction.strip().lower()
            
            # Check restrictions that use AI dietary information.
            check = self.__checks.get(key)
    
            if check is not None:
                actual = self._to_bool(
                    dietary_info[check.ai_field]
                )

                if actual != check.required_value:
                    failures.append(check.warning)

            # Check restrictions using the allergen dictionary.
            allergens = ALLERGEN_RESTRICTIONS.get(key)
            
            if allergens is not None:
                for ingredient in recipe_ingredients:
                    for allergen in allergens:
                        matched = self._find_allergen_matches(
                            ingredient, allergen
                        )

                        if matched:
                            failures.append(
                                f"The recipe contains {ingredient}, "
                                f"which may contain {allergen}."
                            )

            # If neither method supports the restriction,
            # mark it as unverified.
            if check is None and allergens is None:
                unverified.append(restriction)

        # Remove duplicate warning messages.
        warnings = list(dict.fromkeys(failures))

        if unverified:
            warnings.append(
                "Could not verify these restrictions: "
                + ", ".join(unverified) + "."
            )

        return RuleResult(
            passed=not failures,
            warning=" ".join(warnings) if warnings else None
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

class LogicManager:
 
    def __init__(self, rules: list[RecipeRule] | None = None):
        # Composition: the manager owns its rules. Defaults are built here,
        # but callers may supply their own (open for extension).
        self.__rules = list(rules) if rules is not None else self._default_rules()
 
    @staticmethod
    def _default_rules() -> list[RecipeRule]:
        return [
            CookingTimeRule(),
            DietaryRestrictionRule(),
            MainIngredientRule(),
            ServingsRule(),
            MeasurementRule(),
            BreakfastPreferenceRule(),
        ]
 
    def _run_rule(self, rule: RecipeRule, user_preferences: dict, ai_response: dict) -> RuleResult:
        # Enforces the RecipeRule contract: always returns a RuleResult,
        # so malformed AI output cannot crash the application.
        try:
            return rule.evaluate(user_preferences, ai_response)
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            return RuleResult(
                passed=False,
                warning=f"{rule.name} could not be evaluated ({type(error).__name__}: {error}).",
            )
 
    def evaluate_recipe(self, user_preferences: dict, ai_response: dict) -> EvaluationResult:
        # Polymorphism: every rule is used through the RecipeRule interface
        results = [
            self._run_rule(rule, user_preferences, ai_response)
            for rule in self.__rules
        ]
 
        warnings = [r.warning for r in results if r.warning]
        combined_warning = " ".join(warnings) if warnings else None
        total_score = sum(r.score for r in results)
 
        if any(not r.passed for r in results):
            return EvaluationResult(
                Status.REJECT,
                "Recipe does not meet all requirements.",
                total_score,
                combined_warning,
            )
 
        return EvaluationResult(
            Status.ACCEPT,
            "Recipe meets all requirements.",
            total_score,
            combined_warning,
        )

if __name__ == "__main__":
    import json

    with open("test_script_user_input.json", "r") as file:
        user_preferences = json.load(file)

    with open("test_script_AI.json", "r") as file:
        ai_response = json.load(file)

    result = LogicManager().evaluate_recipe(user_preferences, ai_response)
    print(result.to_dict())

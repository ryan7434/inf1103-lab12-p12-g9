from recipe_rule_logic_manager import RecipeRule
from rule_result_logic_manager import RuleResult
from dietary_check_logic_manager import DietaryCheck

import re
from dictionary import INGREDIENT_ALLERGENS, ALLERGEN_RESTRICTIONS


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

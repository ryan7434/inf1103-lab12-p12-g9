from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult
from logic_layer.dietary_check_logic_manager import DietaryCheck

import re
from Io_layer.dictionary import (
    INGREDIENT_ALLERGENS,
    ALLERGEN_RESTRICTIONS,
    IngredientCatalog,
)


DEFAULT_DIETARY_CHECKS = {
    "halal": DietaryCheck("halal_suitable", True, "The recipe may not be halal."),
    "no peanuts": DietaryCheck("contains_peanuts", False, "The recipe contains peanuts."),
}


class DietaryRestrictionRule(RecipeRule):

    #additional spellings for allergen-category names.
    ALLERGEN_ALIASES = {
        "peanut": "peanuts",
        "no peanut": "no peanuts",
        "egg": "eggs",
        "no egg": "no eggs",
        "nut": "nuts",
        "no nut": "no nuts",
        "tree nut": "tree nuts",
        "no tree nut": "no tree nuts",
    }

    def __init__(self):
        self.__checks = DEFAULT_DIETARY_CHECKS
        self._catalog = IngredientCatalog()

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]

        return bool(value)

    def _normalise(self, value):
        return self._catalog.normalise(value)

    @staticmethod
    def _contains_phrase(text, phrase):
        #match complete words or phrases instead of partial words
        return bool(
            phrase
            and re.search(
                rf"(?<!\w){re.escape(phrase)}(?!\w)",
                text,
            )
        )

    def _allergen_key(self, restriction):
        key = " ".join(restriction.lower().split())
        return self.ALLERGEN_ALIASES.get(key, key)

    def _find_allergen_matches(self, ingredient, allergen):
        matches = []

        for key, allergens in INGREDIENT_ALLERGENS.items():

            #check whether this ingredient is associated with the allergen being searched for
            if allergen in allergens:

                #match the ingredient name or phrase
                if self._contains_phrase(
                    ingredient,
                    self._normalise(key),
                ):
                    matches.append(key)

        return matches

    def evaluate(self, user_preferences, ai_response):

        dietary_info = ai_response["dietary_information"]

        failures = []
        unverified = []

        #extract the recipe ingredient names
        recipe_ingredients = [
            self._normalise(item["name"])
            for item in ai_response["ingredients"]
        ]

        #check seasonings as well as the main ingredient list
        recipe_ingredients.extend(
            self._normalise(seasoning)
            for seasoning in ai_response.get("seasonings", [])
        )
        recipe_ingredients = list(dict.fromkeys(recipe_ingredients))

        #preserve the full exclusion list, including custom foods
        restricted_ingredients = list(
            dict.fromkeys(
                self._normalise(item)
                for item in user_preferences.get(
                    "restricted_ingredients", []
                )
            )
        )

        #reject direct matches even when the food is not in the allergen dictionary
        for restriction in restricted_ingredients:
            for ingredient in recipe_ingredients:
                if self._contains_phrase(ingredient, restriction):
                    failures.append(
                        f"The recipe contains {ingredient}, "
                        f"which matches your exclusion: {restriction}."
                    )

        #check each dietary restriction selected by the user
        dietary_restrictions = list(
            dict.fromkeys(
                self._allergen_key(restriction)
                for restriction in user_preferences.get(
                    "dietary_restrictions", []
                )
            )
        )

        for key in dietary_restrictions:

            #check restrictions that use AI dietary information
            check = self.__checks.get(key)

            if check is not None:
                actual = self._to_bool(
                    dietary_info[check.ai_field]
                )

                if actual != check.required_value:
                    failures.append(check.warning)

            allergens = ALLERGEN_RESTRICTIONS.get(key)

            #if neither method supports the restriction mark it as unverified
            if check is None and allergens is None:
                unverified.append(key)

        #resolve supported allergen categories from both lists
        #for example, "peanut" resolves to the "peanuts" category
        allergen_categories = set()

        for restriction in dietary_restrictions + restricted_ingredients:
            key = self._allergen_key(restriction)
            allergen_categories.update(
                ALLERGEN_RESTRICTIONS.get(key, [])
            )

        #check restrictions using the allergen dictionary
        for allergen in sorted(allergen_categories):
            for ingredient in recipe_ingredients:
                matched = self._find_allergen_matches(
                    ingredient, allergen
                )

                if matched:
                    failures.append(
                        f"The recipe contains {ingredient}, "
                        f"which may contain {allergen}."
                    )

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
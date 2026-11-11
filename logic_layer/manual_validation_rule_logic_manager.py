import re

from Io_layer.dictionary import IngredientCatalog
from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult


class ManualValidationRule(RecipeRule):
    #flag vague compound names, not every named sauce or seasoning

    VAGUE_DESCRIPTORS = (
        "signature",
        "special",
    )

    COMPOUND_TERMS = (
        "sauce",
        "sauces",
        "dressing",
        "dressings",
        "paste",
        "pastes",
        "marinade",
        "marinades",
        "seasoning",
        "seasonings",
        "mix",
        "mixes",
        "blend",
        "blends",
        "stock",
        "broth",
        "condiment",
        "condiments",
        "spread",
        "spreads",
        "dip",
        "dips",
    )

    GENERIC_NAMES = frozenset({
        "sauce",
        "dressing",
        "paste",
        "marinade",
        "seasoning",
        "seasonings",
        "mix",
        "blend",
        "stock",
        "broth",
        "condiment",
        "spread",
        "dip",
        "seasoning mix",
        "seasoning blend",
        "spice mix",
        "spice blend",
        "mixed spices",
        "sauce mix",
        "dressing mix",
        "curry paste",
    })

    def __init__(self):
        self._catalog = IngredientCatalog()

    @staticmethod
    def _contains_phrase(text, phrase):
        return bool(
            re.search(
                rf"(?<!\w){re.escape(phrase)}(?!\w)",
                text,
            )
        )

    def _needs_review(self, name):
        #generic names do not identify the full composition
        if name in self.GENERIC_NAMES:
            return True

        #flag names such as "special sauce" or "house dressing"
        has_vague_descriptor = any(
            self._contains_phrase(name, word)
            for word in self.VAGUE_DESCRIPTORS
        )

        has_compound_term = any(
            self._contains_phrase(name, word)
            for word in self.COMPOUND_TERMS
        )

        return has_vague_descriptor and has_compound_term

    def evaluate(self, user_preferences, ai_response):
        #explicitly entered exclusions activate manual validation
        exclusions = list(
            dict.fromkeys(
                self._catalog.normalise(item)
                for item in user_preferences.get(
                    "custom_exclusions", []
                )
                if item.strip()
            )
        )

        if not exclusions:
            return RuleResult(passed=True)

        names = [
            self._catalog.normalise(item["name"])
            for item in ai_response["ingredients"]
        ]

        names.extend(
            self._catalog.normalise(item)
            for item in ai_response.get("seasonings", [])
        )

        manual_validation = []

        for name in dict.fromkeys(names):
            if self._needs_review(name):
                manual_validation.append({
                    "ingredient": name,
                    "exclusions_to_check": list(exclusions),
                    "reason": (
                        "Vague ingredient name; composition is not available. "
                        "Check the ingredient list or confirm with the supplier."
                    ),
                    "status": "pending",
                })

        #dietaryRestrictionRule still rejects known conflicts
        return RuleResult(
            passed=True,
            manual_validation=manual_validation,
        )
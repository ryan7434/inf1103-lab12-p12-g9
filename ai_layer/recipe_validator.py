import math
from typing import Any
from .response_validator import ResponseValidator

# Checks recipe structure and core numeric values.
# Suitability for the user remains the logic layer's responsibility.
class RecipeValidator(ResponseValidator):
    """Validate recipe fields, ingredient structure and core numbers."""

# Every recipe must contain these fields, each with the listed Python type.
    REQUIRED_FIELDS = {
        "recipe_name": str,
        "ingredients": list,
        "description": str,
        "seasonings": list,
        "instructions": list,
        "estimated_cooking_time_minutes": (int, float),
        "servings": (int, float),
        "is_breakfast": bool,
    }

    # Every ingredient inside a recipe must have these three text fields
    INGREDIENT_FIELDS = ("name", "quantity", "unit")

    # A recipe is valid only if ALL of these checks pass.
    def is_valid(self, recipe: Any) -> bool:
        return (
            isinstance(recipe, dict)
            and self._has_required_fields(recipe)
            and self._is_finite_number(
                recipe["estimated_cooking_time_minutes"])
            and recipe["estimated_cooking_time_minutes"] >= 0
            and self._is_finite_number(recipe["servings"])
            and recipe["servings"] > 0
            and self._ingredients_are_valid(recipe["ingredients"])
            and self._text_items_are_valid(
                recipe["instructions"], allow_empty_list=False
            )
            and self._text_items_are_valid(
                recipe["seasonings"], allow_empty_list=True
            )
        )
    
    def _has_required_fields(self, recipe: dict) -> bool:
        for field, expected in self.REQUIRED_FIELDS.items():
            if field not in recipe:
                return False
            expected_types = (
                expected if isinstance(expected, tuple) else (expected,)
            )
            value = recipe[field]
            # Reject booleans where a numeric value is expected.
            if isinstance(value, bool) and bool not in expected_types:
                return False
            if not isinstance(value, expected_types):
                return False
        return True

    @staticmethod
    def _is_finite_number(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False

        try:
            return math.isfinite(float(value))
        except (OverflowError, ValueError):
            return False

    def _ingredients_are_valid(self, ingredients: list) -> bool:
        if not ingredients:
            return False
        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                return False
            for field in self.INGREDIENT_FIELDS:
                value = ingredient.get(field)
                if not isinstance(value, str) or not value.strip():
                    return False
        return True

    @staticmethod
    def _text_items_are_valid(
        items: list, allow_empty_list: bool
    ) -> bool:
        if not items:
            return allow_empty_list
        return all(
            isinstance(item, str) and item.strip()
            for item in items
        )
from typing import Any

from .response_validator import ResponseValidator

# Checks that one recipe from the AI has all the fields, with the right types
# and no empty values. It checks structure only, not whether the recipe is
# suitable for the user (that is the logic layer's job).
class RecipeValidator(ResponseValidator):
    """Structural check for one recipe dict (fields, types, non-empty values)."""

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
    # Every ingredient inside a recipe must have these three text fields.
    INGREDIENT_FIELDS = ("name", "quantity", "unit")

    # A recipe is valid only if ALL of these checks pass.
    def is_valid(self, recipe: Any) -> bool:
        return (
            isinstance(recipe, dict)
            and self._has_required_fields(recipe)
            and self._ingredients_are_valid(recipe["ingredients"])
            and self._text_items_are_valid(recipe["instructions"], allow_empty_list=False)
            and self._text_items_are_valid(recipe["seasonings"], allow_empty_list=True)
        )

     # Check that each required field exists and has the correct type.
    def _has_required_fields(self, recipe: dict) -> bool:
        for field, expected in self.REQUIRED_FIELDS.items():
            if field not in recipe:
                return False
            # Turn a single type into a tuple so isinstance() can handle both cases.
            expected_types = expected if isinstance(expected, tuple) else (expected,)
            value = recipe[field]
            # bool is a subclass of int, so True would otherwise pass as a number
            if isinstance(value, bool) and bool not in expected_types:
                return False
            if not isinstance(value, expected_types):
                return False
        return True

    # The ingredient list must not be empty, and every ingredient needs
    # a non-blank name, quantity and unit (all strings).
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

    # Used for instructions and seasonings: every item must be a non-blank string.
    # allow_empty_list decides whether an empty list is acceptable
    # (instructions: no, seasonings: yes).
    @staticmethod
    def _text_items_are_valid(items: list, allow_empty_list: bool) -> bool:
        if not items:
            return allow_empty_list
        return all(isinstance(item, str) and item.strip() for item in items)

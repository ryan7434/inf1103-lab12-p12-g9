from datetime import datetime
from fractions import Fraction

from dictionary import (
    DIETARY_CHOICES,
    HALAL_RESTRICTED_INGREDIENTS,
    IngredientCatalog,
)


class RecipeTranslator:
    """Converts data between the dict shapes each manager expects (adapter)."""

    def __init__(self, catalog=None):
        self._catalog = catalog if catalog is not None else IngredientCatalog()

    def normalise(self, name):
        """Lowercase, collapse spaces and resolve aliases, so 'Eggs' == 'egg'."""
        return self._catalog.normalise(str(name))

    # io_manager -> ai_manager
    def to_ai_input(self, req, restricted_ingredients):
        # Decimal is not JSON-serialisable, so quantities become strings here.
        ingredients = [
            {
                "name": ingredient["name"],
                "quantity": str(ingredient["quantity"]),
                "unit": ingredient["unit"],
            }
            for ingredient in req["ingredients"]
        ]

        return {
            "ingredients": ingredients,
            "dietary_restrictions": list(restricted_ingredients),
            "cuisine": req["cuisine"],
            "meal_type": "Breakfast" if req["breakfast"] else "Any",
            "taste_preference": ", ".join(req["tastes"]),
            "max_cooking_time": req["max_time"],
            "servings": req["servings"],
        }

    # io_manager -> logic_manager
    def dietary_keys(self, req):
        """The restriction keys that DietaryRestrictionRule understands."""
        keys = []
        dietary = req["dietary"]
        choice = dietary["dietary_choice"]

        if choice is not None and DIETARY_CHOICES[choice]["key"] == "halal":
            keys.append("halal")

        if any("peanut" in self.normalise(item) for item in dietary["custom_exclusions"]):
            keys.append("no peanuts")

        return keys

    def to_logic_preferences(self, req, restricted_ingredients):
        return {
            "maximum_cooking_time": req["max_time"],
            "dietary_restrictions": self.dietary_keys(req),
            "restricted_ingredients": list(restricted_ingredients),
            "custom_exclusions": list(req["dietary"]["custom_exclusions"]),
            "breakfast_preferred": req["breakfast"],
            # the rules compare numbers, so Decimal becomes float here
            "available_ingredients": [
                {
                    "name": self.normalise(ingredient["name"]),
                    "amount": float(ingredient["quantity"]),
                    "unit": ingredient["unit"],
                }
                for ingredient in req["ingredients"]
            ],
            "servings": req["servings"],
        }

    # ai_manager -> logic_manager
    def to_logic_response(self, recipe):
        """Raises ValueError if an ingredient quantity cannot be read."""
        ingredients = [
            {
                "name": self.normalise(item.get("name", "")),
                "amount": self._to_float(item.get("quantity")),
                "unit": item.get("unit", ""),
            }
            for item in recipe.get("ingredients", [])
        ]

        return {
            "cooking_time_minutes": recipe.get("estimated_cooking_time_minutes", 0),
            "dietary_information": self._derive_dietary_information(recipe),
            "is_breakfast": recipe["is_breakfast"],
            "main_ingredients_used": [item["name"] for item in ingredients],
            "servings": recipe.get("servings", 0),
            "ingredients": ingredients,
            "seasonings": recipe.get("seasonings", []),
        }

    # accepted recipe -> data_manager
    def to_record(self, record_id, recipe, req, ai_input):
        user_names = {self.normalise(item["name"]) for item in req["ingredients"]}
        recipe_names = [
            self.normalise(item.get("name", ""))
            for item in recipe.get("ingredients", [])
        ]
        used = [name for name in recipe_names if name in user_names]
        missing = [name for name in recipe_names if name not in user_names]

        return {
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "dish_name": recipe.get("recipe_name", ""),
            "matched_ingredients_count": len(used),
            "used_ingredients": used,
            "missing_ingredients": missing,
            "seasonings_suggested": recipe.get("seasonings", []),
            "cooking_time_mins": recipe.get("estimated_cooking_time_minutes", 0),
            "servings": recipe.get("servings", 0),
            "cuisine": ai_input["cuisine"],
            "meal_type": ai_input["meal_type"],
            "taste_preference": ai_input["taste_preference"],
            "dietary_restrictions": ai_input["dietary_restrictions"],
            "ai_insight": recipe.get("description", ""),
            "instructions": recipe.get("instructions", []),
        }

    def _derive_dietary_information(self, recipe):
        """The AI schema does not ask for halal/peanut flags, so work them out."""
        names = [
            self.normalise(item.get("name", ""))
            for item in recipe.get("ingredients", [])
        ] + [self.normalise(seasoning) for seasoning in recipe.get("seasonings", [])]

        halal_violation = any(name in HALAL_RESTRICTED_INGREDIENTS for name in names)
        contains_peanuts = any("peanut" in name for name in names)

        return {
            "halal_suitable": "False" if halal_violation else "True",
            "contains_peanuts": "True" if contains_peanuts else "False",
        }

    @staticmethod
    def _to_float(value):
        # accepts "2", "1.5" or "1/2"; anything else is a ValueError
        try:
            amount = float(Fraction(value))
            if amount > 0 and not isinstance(value, bool):
                return amount
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            pass
        raise ValueError(f"Invalid quantity: {value!r}")

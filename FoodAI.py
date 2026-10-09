from datetime import datetime

import IO_manager
import AiManager
import logic_manager
import data_manager

from dictionary import (
    DIETARY_CHOICES,
    HALAL_RESTRICTED_INGREDIENTS,
    INGREDIENT_ALIASES,
)

# io_manager -> ai_manager
def build_ai_manager_input(req):
    """
    Convert the req dict from io_manager.main() into the flat dict shape
    ai_manager.generate_recipes() expects.
    """
    # Resolve the dietary category + custom exclusions into one flat list of restricted ingredient names
    restricted_ingredients = sorted(
        IO_manager.get_all_restricted_ingredients(req["dietary"])
    )

    # Convert Decimal quantities to strings. Decimal is NOT JSON-serialisable - json.dumps() raises TypeError on it - so we stringify it here rather than passing it through to ai_manager as Decimal.
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
        "dietary_restrictions": restricted_ingredients,
        "cuisine": req["cuisine"],
        "meal_type": "Breakfast" if req["breakfast"] else "Any",
        # ai_manager expects one taste string
        "taste_preference": ", ".join(req["tastes"]),
        "max_cooking_time": req["max_time"],
        "servings": req["servings"],
    }
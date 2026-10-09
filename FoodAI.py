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

# io_manager/ai_manager -> logic_manager
def _normalise_ingredient_name(name):
    """Same normalisation io_manager applies: lowercase, collapse spaces,
    resolve through the alias table, so e.g. 'Eggs' and 'egg' compare equal."""
    cleaned = " ".join(str(name).lower().split())
    return INGREDIENT_ALIASES.get(cleaned, cleaned)

def resolve_dietary_keys(req):
    """
    logic_manager.validate_dietary_restriction() only understands two
    literal restriction keys: "halal" and "no peanuts".
    """
    keys = []
    dietary = req["dietary"]
    choice = dietary["dietary_choice"]

    if choice is not None:
        category_key = DIETARY_CHOICES[choice]["key"]
        if category_key == "halal":
            keys.append("halal")

    if any("peanut" in _normalise_ingredient_name(item) for item in dietary["custom_exclusions"]):
        keys.append("no peanuts")

    return keys

def build_logic_manager_user_preference(req):
    """
    Convert io_manager's req dict into the user_preference shape
    logic_manager's validation functions expect.
    """
    return {
        "maximum_cooking_time": req["max_time"],
        "dietary_restrictions": resolve_dietary_keys(req),
        "breakfast_preferred": req["breakfast"],
        # logic_manager does numeric comparisons (recipe_amount > user_amount),
        # so Decimal is converted to float here rather than passed through
        "available_ingredients": [
            {
                "name": ingredient["name"],
                "amount": float(ingredient["quantity"]),
                "unit": ingredient["unit"],
            }
            for ingredient in req["ingredients"]
        ],
        "servings": req["servings"],
    }

def _derive_dietary_information(recipe):
    """
    logic_manager expects ai_response["dietary_information"] with
    "halal_suitable"/"contains_peanuts" string flags, but ai_manager's
    schema never asks the model to self-report this information. Derive it from the recipe's ingredients and seasonings.
    """
    names = [
        _normalise_ingredient_name(ingredient.get("name", ""))
        for ingredient in recipe.get("ingredients", [])
    ] + [
        _normalise_ingredient_name(seasoning)
        for seasoning in recipe.get("seasonings", [])
    ]

    halal_violation = any(name in HALAL_RESTRICTED_INGREDIENTS for name in names)
    contains_peanuts = any("peanut" in name for name in names)

    return {
        "halal_suitable": "False" if halal_violation else "True",
        "contains_peanuts": "True" if contains_peanuts else "False",
    }

def build_logic_manager_ai_response(recipe, requested_meal_type):
    """
    Convert one ai_manager recipe dict into the ai_response shape
    logic_manager's validation functions expect.
    """
    ingredients = []
    for ingredient in recipe.get("ingredients", []):
        try:
            # ai_manager's schema defines quantity as a STRING 
            # logic_manager needs a number to do recipe_amount > user_amount comparisons.
            amount = float(ingredient.get("quantity", 0))
        except (TypeError, ValueError):
            amount = 0.0
        ingredients.append({
            "name": ingredient.get("name", ""),
            "amount": amount,
            "unit": ingredient.get("unit", ""),
        })

    return {
        "cooking_time_minutes": recipe.get("estimated_cooking_time_minutes", 0),
        "dietary_information": _derive_dietary_information(recipe),
        # ai_manager doesn't report whether a recipe "is" breakfast - but we already told it which meal_type to generate for, so a recipe coming back from a "Breakfast" request is treated as breakfast.
        "is_breakfast": requested_meal_type == "Breakfast",
        "main_ingredients_used": [
            ingredient.get("name", "") for ingredient in recipe.get("ingredients", [])
        ],
        "servings": recipe.get("servings", 0),
        "ingredients": ingredients,
    }

# recipe + context -> data_manager
def build_data_manager_record(record_id, recipe, req, ai_input):

    #Convert one accepted recipe into the flat dict shape data_manager.save_processed_record() expects for CSV storage.

    user_ingredient_names = {
        _normalise_ingredient_name(ingredient["name"]) for ingredient in req["ingredients"]
    }
    recipe_ingredient_names = [
        _normalise_ingredient_name(ingredient.get("name", ""))
        for ingredient in recipe.get("ingredients", [])
    ]

    used = [name for name in recipe_ingredient_names if name in user_ingredient_names]
    missing = [name for name in recipe_ingredient_names if name not in user_ingredient_names]

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
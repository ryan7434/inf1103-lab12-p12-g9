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

from fractions import Fraction


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
    Convert the IO manager's request into the format expected
    by the logic manager.
    """
    return {
        "maximum_cooking_time": req["max_time"],

        #full category restrictions plus custom exclusions.
        "restricted_ingredients": sorted(
            IO_manager.get_all_restricted_ingredients(req["dietary"])
        ),

        "breakfast_preferred": req["breakfast"],
        #logic_manager does numeric comparisons (recipe_amount > user_amount),
        #decimal is converted to float here rather than passed through
        "available_ingredients": [
            {
                "name": _normalise_ingredient_name(
                    ingredient["name"]
                ),
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


def _to_float(value):
    #parse a positive quantity: "2", "1.5" or "1/2" and raises ValueError for any invalid results
    try:
        amount = float(Fraction(value))
        if amount > 0 and not isinstance(value, bool):
            return amount
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        pass
    raise ValueError(f"Invalid quantity: {value!r}")


def build_logic_manager_ai_response(recipe, requested_meal_type):
    """
    Convert one ai_manager recipe dict into the ai_response shape
    logic_manager's validation functions expect.
    """
    ingredients = [
        {
            "name": _normalise_ingredient_name(i.get("name", "")),
            "amount": _to_float(i.get("quantity")),
            "unit": i.get("unit", ""),
        }
        for i in recipe.get("ingredients", [])
    ]

    return {
        "cooking_time_minutes": recipe.get("estimated_cooking_time_minutes", 0),
        "dietary_information": _derive_dietary_information(recipe),
        #reflects the requested meal type, not an independent check
        #of whether the generated recipe is breakfast.
        "is_breakfast": requested_meal_type == "Breakfast",
        #reuse the names already normalised above.
        "main_ingredients_used": [i["name"] for i in ingredients],
        "servings": recipe.get("servings", 0),
        "ingredients": ingredients,
        #allow the dietary validator to check seasonings too.
        "seasonings": recipe.get("seasonings", []),
    }


def build_data_manager_record(record_id, recipe, req, ai_input):
    """
    Convert one accepted recipe into the flat dict shape
    data_manager.save_processed_record() expects
    """
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


def main():
    # Step 1: collect and confirm the user's request.
    request = IO_manager.main()
 
    # Step 2: translate it into ai_manager's expected shape, then
    # generate candidate recipes via the AI layer.
    ai_input = build_ai_manager_input(request)
    recipes = AiManager.generate_recipes(ai_input)
 
    if not recipes:
        print(
            "\nSorry, we couldn't generate any recipes right now. "
            "Please check ai_manager_errors.log or try again shortly."
        )
        return
 
    # Step 3: validate each candidate recipe against the user's hard
    # requirements (cooking time, dietary/halal safety, ingredient
    # overlap, servings, measurements) via logic_manager.
    user_preference = build_logic_manager_user_preference(request)
 
    accepted = []

    for recipe in recipes:
        if not AiManager.validate_recipe_schema(recipe):
            recipe_name = (
                recipe.get("recipe_name", "Unnamed recipe")
                if isinstance(recipe, dict)
                else "Unnamed recipe"
            )
            print(
                f"\nSkipping '{recipe_name}' because its recipe "
                "data is malformed."
            )
            continue

        recipe_name = recipe.get("recipe_name", "Unnamed recipe")

        # Convert the AI recipe into the logic manager's expected format.
        # Skip the recipe if its ingredient quantities cannot be parsed.
        try:
            ai_response = build_logic_manager_ai_response(
                recipe,
                ai_input["meal_type"],
            )
        except ValueError as error:
            print(
                f"\nSkipping '{recipe_name}' because its ingredient "
                f"quantities are invalid: {error}"
            )
            continue

        # Check the recipe against the user's preferences and ingredients.
        evaluation = logic_manager.evaluate_recipe(
            user_preference,
            ai_response,
        )

        if evaluation["status"] == "ACCEPT":
            accepted.append((recipe, evaluation))

    if not accepted:
        print("\nNo recipes passed validation.")
        return
    
    # Step 4: persist each accepted recipe via data_manager.
    existing_records = data_manager.load_all_records()
    next_id = len(existing_records) + 1

    print(f"\n{len(accepted)} of {len(recipes)} generated recipe(s) passed validation:\n")
    for recipe, evaluation in accepted:
        record = build_data_manager_record(next_id, recipe, request, ai_input)
        saved = data_manager.save_processed_record(record)

        print("=" * 60)
        print(
            f"{recipe.get('recipe_name')} "
            f"({recipe.get('estimated_cooking_time_minutes')} min, "
            f"serves {recipe.get('servings')})"
        )
        print("=" * 60)

        if recipe.get("description"):
            print(f"\n{recipe['description']}")

        ingredients = recipe.get("ingredients", [])
        if ingredients:
            print("\nIngredients:")
            for ingredient in ingredients:
                print(
                    f"  - {ingredient.get('quantity', '')} "
                    f"{ingredient.get('unit', '')} "
                    f"{ingredient.get('name', '')}".rstrip()
                )

        seasonings = recipe.get("seasonings", [])
        if seasonings:
            print("\nSeasonings:")
            for seasoning in seasonings:
                print(f"  - {seasoning}")

        instructions = recipe.get("instructions", [])
        if instructions:
            print("\nInstructions:")
            for step_number, step in enumerate(instructions, start=1):
                print(f"  {step_number}. {step}")

        if evaluation["warning"]:
            print(f"\nNote: {evaluation['warning']}")
        if not saved:
            print("\n(Warning: could not save this recipe to recipes_history.csv)")
 
        print()
        next_id += 1


if __name__ == "__main__":
    main()

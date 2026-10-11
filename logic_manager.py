from dictionary import MEASUREMENT_UNITS, INGREDIENT_ALIASES
import json

# Load the AI response from the test script
# with open('test_script_AI.json', 'r') as f:
    # ai_response = json.load(f)

# with open('test_script_user_input.json', 'r') as f:
    # user_response = json.load(f)

# maximum cooking time validation
def validate_cooking_time(user_preference, ai_response):
    max_time = user_preference["maximum_cooking_time"]
    ai_time = ai_response["cooking_time_minutes"]

    if ai_time > max_time:
        return {
            "passed": False,
            "warning": (
                f"The recipe takes {ai_time} minutes, which exceeds your {max_time}-minute limit."
            )
        }
        
    return {
        "passed": True,
        "warning": None
    }

# dietary restrictions validation
def _is_nonempty_str(value):
    return isinstance(value, str) and bool(value.strip())


def validate_dietary_restriction(user_preference, ai_response):
    """Check recipe ingredients and seasonings against all exclusions."""

    def normalise(name):
        cleaned = " ".join(name.lower().split())
        return INGREDIENT_ALIASES.get(cleaned, cleaned)

    restricted = user_preference.get("restricted_ingredients")
    ingredients = ai_response.get("ingredients")
    seasonings = ai_response.get("seasonings")

    # Do not silently approve a recipe when dietary data is malformed.
    if not (
        isinstance(restricted, list)
        and isinstance(ingredients, list)
        and isinstance(seasonings, list)
        and all(map(_is_nonempty_str, restricted))
        and all(map(_is_nonempty_str, seasonings))
        and all(
            isinstance(i, dict) and _is_nonempty_str(i.get("name"))
            for i in ingredients
        )
    ):
        return {
            "passed": False,
            "warning": "Dietary validation failed: missing or malformed "
                       "ingredient data.",
        }

    recipe_names = {normalise(i["name"]) for i in ingredients}
    recipe_names |= {normalise(s) for s in seasonings}
    conflicts = sorted(recipe_names & {normalise(r) for r in restricted})

    if conflicts:
        return {
            "passed": False,
            "warning": "Recipe includes restricted ingredients: "
                       + ", ".join(conflicts) + ".",
        }

    return {"passed": True, "warning": None}

# breakfast preference scoring (soft preference, not a hard validation)
def score_breakfast_preference(user_input, ai_response):
    wants_breakfast = user_input["breakfast_preferred"]
    is_breakfast_recipe = ai_response["is_breakfast"]

    if not wants_breakfast:
        return 0  # no preference stated, no bonus either way

    if is_breakfast_recipe:
        return 1  # matches preference, add to ranking score
    else:
        return 0  # doesn't match, but not rejected

# checks recipe uses at least 3 of the user's ingredient input
def check_main_ingredient(user_preference, ai_response):
    user_ingredient = user_preference["available_ingredients"]
    ai_ingredient = ai_response["main_ingredients_used"]

    match_count = 0

    for ingredient in user_ingredient:
          ingredient_name = ingredient["name"]
          if ingredient_name.lower() in [
              item.lower() for item in ai_ingredient
    ]:
            match_count += 1

    if match_count >= 3:
        return True

    return False

# checks recipe for max 5 servings
def check_max_servings(user_preference, ai_response):
    user_servings = user_preference["servings"]
    ai_servings = ai_response["servings"]

    if ai_servings > 5:
        return {
            "passed": False,
            "warning": f"This recipe serves more than 5 servings."
        }

    if ai_servings < user_servings:
        return {
            "passed": True,
            "warning": f"This recipe can only serve {ai_servings} servings. Proceed only if you are okay with this."
        }

    return {
        "passed": True,
        "warning": None
    }

def check_measurements(user_preference, ai_response):
    warnings = []

    user_ingredients = user_preference["available_ingredients"]

    unit_conversions = {
        "g": ("mass", 1.0),
        "kg": ("mass", 1000.0),
        "ml": ("volume", 1.0),
        "l": ("volume", 1000.0),
    }

    for recipe_item in ai_response["ingredients"]:
        recipe_name = recipe_item["name"].lower()
        recipe_amount = recipe_item["amount"]
        recipe_unit = recipe_item["unit"].strip().lower()

        for user_item in user_ingredients:
            user_name = user_item["name"].lower()

            if recipe_name == user_name:
                user_amount = user_item["amount"]
                user_unit = user_item["unit"].strip().lower()

                #only compare amounts when the units are the same
                if recipe_unit == user_unit:
                    comparable_recipe_amount = recipe_amount
                    comparable_user_amount = user_amount
                else:
                    recipe_conversion = unit_conversions.get(recipe_unit)
                    user_conversion = unit_conversions.get(user_unit)

                    if (
                        recipe_conversion is None
                        or user_conversion is None
                        or recipe_conversion[0] != user_conversion[0]
                    ):
                        warnings.append(
                            f"Cannot check the available quantity of "
                            f"{recipe_name}: the recipe uses "
                            f"{recipe_unit}, but you entered "
                            f"{user_unit}."
                        )
                        break

                    comparable_recipe_amount = (
                        recipe_amount * recipe_conversion[1]
                    )
                    comparable_user_amount = (
                        user_amount * user_conversion[1]
                    )

                tolerance = 1e-9 * max(
                    abs(comparable_recipe_amount),
                    abs(comparable_user_amount),
                )

                if (
                    comparable_recipe_amount - comparable_user_amount
                    > tolerance
                ):
                    warnings.append(
                        f"The recipe requires {recipe_amount} "
                        f"{recipe_unit} of {recipe_name}, but you "
                        f"only have {user_amount} {user_unit}."
                    )

                break

    return {
        "passed": True,
        "warning": "; ".join(warnings) if warnings else None
    }

def evaluate_recipe(user_preferences, ai_response):

    cooking_time_ok = validate_cooking_time(
        user_preferences,
        ai_response
    )

    dietary_ok = validate_dietary_restriction(
        user_preferences,
        ai_response
    )

    ingredients_ok = check_main_ingredient(
        user_preferences,
        ai_response
    )

    servings_ok = check_max_servings(
        user_preferences,
        ai_response
    )

    measurements_ok = check_measurements(
        user_preferences,
        ai_response
    )
    #combine every nonempty warning so one warning does not hide another.
    #uses none when none of the checks produces a warning.
    combined_warning = "; ".join(
        result["warning"]
        for result in (
            servings_ok,
            measurements_ok,
            cooking_time_ok,
            dietary_ok,
        )
        if result["warning"]
    ) or None

    #accept only when all required checks pass.
    #check each dictionary's "passed" value, not the dictionary itself.
    if (
        ingredients_ok
        and servings_ok["passed"]
        and measurements_ok["passed"]
        and cooking_time_ok["passed"]
        and dietary_ok["passed"]
    ):
        return {
            "status": "ACCEPT",
            "reason": "Recipe meets all requirements.",
            "warning": combined_warning
        }
    
    #reject when a required check fails, retaining warnings that were stored in the combined_warning variable.
    return {
        "status": "REJECT",
        "reason": "Recipe does not meet all requirements.",
        "warning": combined_warning
    }


if __name__ == "__main__":
    with open("test_script_user_input.json", "r") as f:
        user_response = json.load(f)
    with open("test_script_AI.json", "r") as f:
        ai_response = json.load(f)

    result = evaluate_recipe(user_response, ai_response)
    print(result)


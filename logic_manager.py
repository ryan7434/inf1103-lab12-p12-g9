from dictionary import MEASUREMENT_UNITS
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
def validate_dietary_restriction(user_preference, ai_response):
    dietary_restrictions = user_preference["dietary_restrictions"]
    dietary_information = ai_response["dietary_information"]

    for restriction in dietary_restrictions:
        if restriction == "halal":
            if dietary_information["halal_suitable"] != "True":
                return {
                    "passed": False,
                    "warning": "The recipe may not be halal."
                }

        elif restriction == "no peanuts":
            if dietary_information["contains_peanuts"] != "False":
                return {
                    "passed": False,
                    "warning": "The recipe contains peanuts."
                }

    return {
        "passed": True,
        "warning": None
    }

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

    for recipe_item in ai_response["ingredients"]:
        recipe_name = recipe_item["name"].lower()
        recipe_amount = recipe_item["amount"]
        recipe_unit = recipe_item["unit"].lower()

        for user_item in user_ingredients:
            user_name = user_item["name"].lower()

            if recipe_name == user_name:
                user_amount = user_item["amount"]
                user_unit = user_item["unit"].lower()

                # Only compare amounts when the units are the same
                if recipe_unit == user_unit:
                    if recipe_amount > user_amount:
                        warnings.append(
                            f"The recipe requires {recipe_amount} {recipe_unit} "
                            f"of {recipe_name}, but you only have "
                            f"{user_amount} {user_unit}."
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

    if ingredients_ok and servings_ok["passed"] and measurements_ok["passed"] and cooking_time_ok and dietary_ok:
        return {
            "status": "ACCEPT",
            "reason": "Recipe meets all requirements.",
            "warning": servings_ok["warning"] or measurements_ok["warning"] or cooking_time_ok["warning"] or dietary_ok["warning"]
        }

    return {
        "status": "REJECT",
        "reason": "Recipe does not meet all requirements.",
        "warning": servings_ok["warning"] or measurements_ok["warning"] or cooking_time_ok["warning"] or dietary_ok["warning"]
    }

result = evaluate_recipe(user_response, ai_response)
print(result)

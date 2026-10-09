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
def validate_dietary_restriction(user_input, ai_response):
    restricted_ingredients = ai_response["restricted_ingredients"]

    if restricted_ingredients:
        return False
    else:
        return True

# other exclusions (e.g allergens) validation
def validate_other_exclusions(user_input, ai_response):
    exclusions = user_input["other_exclusions"]
    ingredients = ai_response["ingredients"]

    for exclusion in exclusions:
        exclusion = exclusion.lower().rstrip("s")

        for ingredient in ingredients:
            ingredient = ingredient.lower().rstrip("s")

            if exclusion in ingredient:
                return False

    return True

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

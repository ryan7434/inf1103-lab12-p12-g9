def check_main_ingredient(user_preference, ai_response):
    user_ingredient = user_preference["available_ingredients"]
    ai_ingredient = ai_response["main_ingredients_used"]

    match_count = 0

    for ingredient in user_ingredient:
          if ingredient.lower() in [
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
            "warning": None
        }

    if ai_servings < user_servings:
        return {
            "passed": True,
            "warning": f"This recipe can only serve {ai_servings} servings."
        }

    return {
        "passed": True,
        "warning": None
    }


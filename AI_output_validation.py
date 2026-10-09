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
    restricted_ingredients = ai_response["restricted_ingredients"]

    if restricted_ingredients:
        return {
            "passed": False,
            "warning": "The recipe contains ingredients that violate your dietary restrictions."
        }

    return {
        "passed": True,
        "warning": None
    }


# other exclusions (e.g allergens) validation
def validate_other_exclusions(user_preference, ai_response):
    exclusions = user_preference["other_exclusions"]
    ingredients = ai_response["ingredients"]

    for exclusion in exclusions:
        exclusion = exclusion.lower().rstrip("s")

        for ingredient in ingredients:
            ingredient_name = ingredient["name"].lower().rstrip("s")

            if exclusion in ingredient_name:
                return {
                    "passed": False,
                    "warning": (
                        f"The recipe contains an excluded ingredient: "
                        f"{ingredient['name']}."
                    )
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

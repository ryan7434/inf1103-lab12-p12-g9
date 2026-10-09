# maximum cooking time validation
def validate_cooking_time(user_input, ai_response):
    max_time = user_input["max_cooking_time"]
    ai_time = ai_response["estimated_cooking_time"]

    if ai_time <= max_time:
        return "Cooking time is valid"
    else:
        return "Cooking time exceeds the limit"


# dietary restrictions validation
def validate_dietary_restriction(user_input, ai_response):
    restricted_ingredients = ai_response["restricted_ingredients"]

    if restricted_ingredients:
        return False
    else:
        return True

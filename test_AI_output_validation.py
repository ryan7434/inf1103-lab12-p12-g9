from AI_output_validation import (
    validate_cooking_time,
    validate_dietary_restriction,
    validate_other_exclusions,
    score_breakfast_preference,
)


def test_cooking_time():
    user_input = {
        "max_cooking_time": 30
    }

    ai_response = {
        "estimated_cooking_time": 25
    }

    assert validate_cooking_time(user_input, ai_response) == "Cooking time is valid"


def test_cooking_time_exceeds_limit():
    user_input = {
        "max_cooking_time": 30
    }

    ai_response = {
        "estimated_cooking_time": 40
    }

    assert validate_cooking_time(user_input, ai_response) == "Cooking time exceeds the limit"


def test_dietary_restriction():
    user_input = {
        "dietary_restriction": "vegetarian"
    }

    ai_response = {
        "restricted_ingredients": []
    }

    assert validate_dietary_restriction(user_input, ai_response) == True


def test_vegan_invalid():
    user_input = {
        "dietary_restriction": "vegan"
    }

    ai_response = {
        "restricted_ingredients": ["milk, eggs"]
    }

    assert validate_dietary_restriction(user_input, ai_response) == False


def test_halal_invalid():
    user_input = {
        "dietary_restriction": "halal"
    }

    ai_response = {
        "restricted_ingredients": ["pork"]
    }

    assert validate_dietary_restriction(user_input, ai_response) == False


def test_no_dietary_restriction():
    user_input = {
        "dietary_restriction": "none"
    }

    ai_response = {
        "restricted_ingredients": []
    }

    assert validate_dietary_restriction(user_input, ai_response) == True


def test_lactose_intolerant_invalid():
    user_input = {
        "dietary_restriction": "lactose intolerant"
    }

    ai_response = {
        "restricted_ingredients": ["regular fresh milk"]
    }

    assert validate_dietary_restriction(user_input, ai_response) == False


def test_exclusion_valid():
    user_input = {
        "other_exclusions": ["peanuts", "mushrooms"]
    }

    ai_response = {
        "ingredients": ["tofu", "soy sauce", "bok choy"]
    }

    assert validate_other_exclusions(user_input, ai_response) == True


def test_exclusion_invalid():
    user_input = {
        "other_exclusions": ["peanut"]
    }

    ai_response = {
        "ingredients": ["peanut butter", "jelly", "bread"]
    }

    assert validate_other_exclusions(user_input, ai_response) == False

def test_breakfast_preferred_and_matches():
    user_input = {"breakfast_preferred": True}
    ai_response = {"is_breakfast": False}
    assert score_breakfast_preference(user_input, ai_response) == 1
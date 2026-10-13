#Test inputs are stored as Python dictionaries and not JSON file
#The data is passed directly to the logic manager without external file dependencies


import copy
import logic_manager as lm

user = {
    "maximum_cooking_time": 30,
    "restricted_ingredients": ["pork", "peanut"],
    "breakfast_preferred": True,
    "available_ingredients": [
        {"name": "egg", "amount": 4, "unit": "pieces"},
        {"name": "spinach", "amount": 200, "unit": "g"},
        {"name": "milk", "amount": 500, "unit": "ml"},
    ],
    "servings": 2,
}

ai = {
    "cooking_time_minutes": 20,
    "is_breakfast": True,
    "main_ingredients_used": ["egg", "spinach", "milk"],
    "servings": 2,
    "ingredients": [
        {"name": "egg", "amount": 2, "unit": "pieces"},
        {"name": "spinach", "amount": 100, "unit": "g"},
        {"name": "milk", "amount": 200, "unit": "ml"},
    ],
    "seasonings": ["salt", "pepper"],
}


def variant(base, **changes):
    #copy of base with some fields replaced.
    return {**copy.deepcopy(base), **changes}


def ingredient_variant(index, **changes):
    #copy of ai with one ingredient's fields replaced
    d = copy.deepcopy(ai)
    d["ingredients"][index].update(changes)
    return d


#shared variants
invalid_ai = variant(ai, cooking_time_minutes=user["maximum_cooking_time"] + 1)
restricted_user = variant(user, restricted_ingredients=["milk"])
non_breakfast_ai = variant(ai, is_breakfast=False)
few_ingredients_ai = variant(ai, main_ingredients_used=["egg", "milk"])
too_many_servings_ai = variant(ai, servings=6)
shortage_ai = ingredient_variant(
    0, amount=user["available_ingredients"][0]["amount"] + 1
)

#cooking time
assert lm.validate_cooking_time(user, ai)["passed"] is True
assert lm.validate_cooking_time(user, invalid_ai)["passed"] is False
print("PASS: cooking-time validation")

#dietary restrictions (ingredients and seasonings)
assert lm.validate_dietary_restriction(user, ai)["passed"] is True
assert lm.validate_dietary_restriction(restricted_user, ai)["passed"] is False, \
    "Restricted milk should be detected."
soy_user = variant(user, restricted_ingredients=["soy sauce"])
soy_ai = variant(ai, seasonings=ai["seasonings"] + ["soy sauce"])
assert lm.validate_dietary_restriction(soy_user, soy_ai)["passed"] is False, \
    "Restricted seasoning should be detected."
print("PASS: dietary validation")

#breakfast scoring
assert lm.score_breakfast_preference(user, ai) == 1
assert lm.score_breakfast_preference(user, non_breakfast_ai) == 0
assert lm.score_breakfast_preference(
    variant(user, breakfast_preferred=False), ai
) == 0
print("PASS: breakfast scoring")

#main ingredient overlap
assert lm.check_main_ingredient(user, ai) is True
assert lm.check_main_ingredient(user, few_ingredients_ai) is False
print("PASS: ingredient overlap")

#servings
assert lm.check_max_servings(user, ai)["passed"] is True
assert lm.check_max_servings(user, too_many_servings_ai)["passed"] is False
result = lm.check_max_servings(user, variant(ai, servings=1))
assert result["passed"] is True and result["warning"] is not None, \
    "Fewer servings should pass with a warning."
print("PASS: servings validation")

#quantities and measurement conversion
result = lm.check_measurements(user, ai)
assert result["passed"] is True and result["warning"] is None

result = lm.check_measurements(user, shortage_ai)
assert result["passed"] is True and "only have" in (result["warning"] or ""), \
    "Shortage should be warning-only."

for index, amount, unit in [(1, 0.1, "kg"), (2, 0.2, "L")]:
    result = lm.check_measurements(
        user, ingredient_variant(index, amount=amount, unit=unit)
    )
    assert result["warning"] is None, f"{amount} {unit} should fit."

result = lm.check_measurements(user, ingredient_variant(1, unit="ml"))
assert result["passed"] is True and "Cannot check" in (result["warning"] or ""), \
    "Incompatible units should be warning-only."
print("PASS: quantity checking")

#overall evaluation
result = lm.evaluate_recipe(user, ai)
assert result["status"] == "ACCEPT" and result["warning"] is None

for u, a, why in [
    (user, invalid_ai, "over-limit time"),
    (restricted_user, ai, "restricted ingredient"),
    (user, few_ingredients_ai, "insufficient overlap"),
    (user, too_many_servings_ai, "too many servings"),
]:
    assert lm.evaluate_recipe(u, a)["status"] == "REJECT", f"Should reject: {why}."

result = lm.evaluate_recipe(user, shortage_ai)
assert result["status"] == "ACCEPT" and result["warning"] is not None, \
    "Quantity warning alone should not reject."
assert lm.evaluate_recipe(user, non_breakfast_ai)["status"] == "ACCEPT", \
    "Breakfast mismatch is a soft preference."

#multiple warnings are kept.
multi_ai = variant(shortage_ai, servings=1, cooking_time_minutes=31)
result = lm.evaluate_recipe(restricted_user, multi_ai)
assert result["status"] == "REJECT"
for fragment in ["only serve", "only have", "exceeds", "restricted ingredients"]:
    assert fragment in (result["warning"] or ""), f"Missing warning: {fragment!r}"
print("PASS: overall evaluation")

print("\nAll tests passed without calling the live AI.")
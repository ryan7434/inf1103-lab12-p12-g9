"""
test_food_ai.py - tests for the application controller (FoodAI.py).

Run with:
    python -m unittest test_food_ai -v
"""

import json
import unittest
from decimal import Decimal

import FoodAI

def make_request(dietary="none", breakfast=True, max_time=30, servings=2):
    dietary_details = {
        "none": {"dietary_choice": "6", "selected_choices": ["6"], "custom_exclusions": []},
        "halal": {"dietary_choice": "1", "selected_choices": ["1"], "custom_exclusions": []},
        "peanut": {"dietary_choice": "6", "selected_choices": ["5"], "custom_exclusions": ["peanut"]},
    }[dietary]
    return {
        "dietary": dietary_details,
        "ingredients": [
            {"name": "egg", "quantity": Decimal("3"), "unit": "pieces"},
            {"name": "spinach", "quantity": Decimal("100"), "unit": "g"},
            {"name": "cheddar", "quantity": Decimal("50"), "unit": "g"},
        ],
        "breakfast": breakfast,
        "cuisine": "Western",
        "tastes": ["Savoury"],
        "max_time": max_time,
        "servings": servings,
    }

def make_recipe(name="Good omelette", extra=(), minutes=12, servings=2, breakfast=True, quantity="2"):
    ingredients = [
        {"name": "egg", "quantity": quantity, "unit": "pieces"},
        {"name": "spinach", "quantity": "50", "unit": "g"},
        {"name": "cheddar", "quantity": "30", "unit": "g"},
    ] + [{"name": n, "quantity": "20", "unit": "g"} for n in extra]
    return {
        "recipe_name": name,
        "ingredients": ingredients,
        "description": "A savoury dish.",
        "seasonings": ["salt"],
        "instructions": ["Cook it."],
        "estimated_cooking_time_minutes": minutes,
        "servings": servings,
        "is_breakfast": breakfast,
    }

class TestRecipeTranslator(unittest.TestCase):
    def setUp(self):
        self.translator = FoodAI.RecipeTranslator()

    def test_ai_input_turns_decimals_into_strings_and_names_the_meal_type(self):
        ai_input = self.translator.to_ai_input(make_request(breakfast=True), ["bacon"])
        self.assertEqual(ai_input["ingredients"][0], {"name": "egg", "quantity": "3", "unit": "pieces"})
        self.assertEqual(ai_input["meal_type"], "Breakfast")
        self.assertEqual(ai_input["dietary_restrictions"], ["bacon"])
        json.dumps(ai_input)  # must be JSON-serialisable
        self.assertEqual(self.translator.to_ai_input(make_request(breakfast=False), [])["meal_type"], "Any")

    def test_dietary_keys(self):
        self.assertEqual(self.translator.dietary_keys(make_request("none")), [])
        self.assertEqual(self.translator.dietary_keys(make_request("halal")), ["halal"])
        self.assertEqual(self.translator.dietary_keys(make_request("peanut")), ["no peanuts"])

    def test_logic_preferences_carry_the_dietary_keys_and_float_amounts(self):
        prefs = self.translator.to_logic_preferences(make_request("halal"), [])
        self.assertEqual(prefs["dietary_restrictions"], ["halal"])
        self.assertEqual(prefs["available_ingredients"][1]["amount"], 100.0)
        self.assertIsInstance(prefs["available_ingredients"][1]["amount"], float)

    def test_names_are_normalised_through_the_alias_table(self):
        recipe = make_recipe()
        recipe["ingredients"][0]["name"] = "Eggs"
        response = self.translator.to_logic_response(recipe)
        self.assertEqual(response["ingredients"][0]["name"], "egg")

    def test_halal_flag_is_derived_from_ingredients_and_seasonings(self):
        self.assertEqual(
            self.translator.to_logic_response(make_recipe())["dietary_information"]["halal_suitable"], "True"
        )
        with_ham = make_recipe(extra=["ham"])
        self.assertEqual(
            self.translator.to_logic_response(with_ham)["dietary_information"]["halal_suitable"], "False"
        )
        with_wine = make_recipe()
        with_wine["seasonings"] = ["cooking wine"]
        self.assertEqual(
            self.translator.to_logic_response(with_wine)["dietary_information"]["halal_suitable"], "False"
        )

    def test_unreadable_quantities_raise_value_error(self):
        for bad in ("a few", "0", "-1", "1/0", "", None):
            with self.subTest(quantity=bad):
                with self.assertRaises(ValueError):
                    self.translator.to_logic_response(make_recipe(quantity=bad))

if __name__ == "__main__":
    unittest.main(verbosity=2)
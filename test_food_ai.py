"""
test_food_ai.py - tests for the application controller (FoodAI.py).

Run with:
    python -m unittest test_food_ai -v
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

import FoodAI
from ai_manager import AIProvider, AiManager, AITransportError, ErrorLogger, RecipeValidator
from data_manager import JsonDataManager
from IO_manager import IOManager
from logic_manager import LogicManager

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

class ScriptedIO(IOManager):
    """The real IOManager, except that the request comes from the test, not the keyboard."""

    def __init__(self, request):
        super().__init__()
        self._request = request

    def collect_recipe_request(self):
        return self._request

class StubProvider(AIProvider):
    def __init__(self, reply):
        self._reply = reply

    def generate(self, prompt):
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply if isinstance(self._reply, str) else json.dumps(self._reply)

class ListAiManager:
    """Hands back a fixed list, even malformed items the real AiManager would filter out."""

    def __init__(self, recipes):
        self._recipes = recipes
        self._validator = RecipeValidator()

    def generate_recipes(self, user_input):
        return self._recipes

    def is_valid_recipe(self, recipe):
        return self._validator.is_valid(recipe)

class RejectingDataManager(JsonDataManager):
    def save_record(self, record_dict):
        return False

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_path = os.path.join(self.tmp.name, "history.json")
        self.log_path = os.path.join(self.tmp.name, "errors.log")

    def make_app(self, request, replies, data_manager=None, ai_manager=None):
        if ai_manager is None:
            ai_manager = AiManager(
                provider=StubProvider(replies),
                logger=ErrorLogger(log_file=self.log_path),
                sleep=lambda seconds: None,
            )
        return FoodAI.RecipeApp(
            io_manager=ScriptedIO(request),
            ai_manager=ai_manager,
            logic_manager=LogicManager(),
            data_manager=data_manager or JsonDataManager(self.data_path),
        )

    def run_app(self, app):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            app.run()
        return buffer.getvalue()

    def saved(self):
        with open(self.data_path, encoding="utf-8") as handle:
            return json.load(handle)

class TestRecipeAppFlow(AppTestCase):
    def test_accepted_recipes_are_shown_and_saved(self):
        output = self.run_app(self.make_app(make_request(), [make_recipe()]))
        self.assertIn("1 of 1 generated recipe(s) passed validation", output)
        self.assertIn("Good omelette (12 min, serves 2)", output)
        self.assertEqual([r["dish_name"] for r in self.saved()], ["Good omelette"])

    def test_breakfast_dishes_are_listed_first(self):
        recipes = [make_recipe("Pasta bake", breakfast=False), make_recipe("Omelette", breakfast=True)]
        output = self.run_app(self.make_app(make_request(breakfast=True), recipes))
        self.assertLess(output.index("Omelette ("), output.index("Pasta bake ("))

    def test_a_recipe_over_the_time_limit_is_rejected(self):
        recipes = [make_recipe("Quick", minutes=12), make_recipe("Slow", minutes=90)]
        output = self.run_app(self.make_app(make_request(max_time=30), recipes))
        self.assertIn("Quick (12 min", output)
        self.assertNotIn("Slow (90 min", output)
        self.assertIn("1 of 2 generated recipe(s) passed validation", output)

    def test_halal_choice_rejects_a_recipe_with_bacon(self):
        recipes = [make_recipe("Plain"), make_recipe("Bacon bake", extra=["bacon"])]
        output = self.run_app(self.make_app(make_request("halal"), recipes))
        self.assertIn("Plain (", output)
        self.assertNotIn("Bacon bake (", output)

    def test_peanut_exclusion_rejects_peanut_butter(self):
        recipes = [make_recipe("Plain"), make_recipe("Satay", extra=["peanut butter"])]
        output = self.run_app(self.make_app(make_request("peanut"), recipes))
        self.assertIn("Plain (", output)
        self.assertNotIn("Satay (", output)

    def test_message_when_the_ai_cannot_deliver_and_nothing_is_saved(self):
        output = self.run_app(self.make_app(make_request(), AITransportError("down")))
        self.assertIn("couldn't generate any recipes", output)
        self.assertEqual(JsonDataManager(self.data_path).load_records(), [])

    def test_message_when_no_recipe_passes_the_logic_rules(self):
        output = self.run_app(self.make_app(make_request(max_time=30), [make_recipe(minutes=90)]))
        self.assertIn("No recipes passed validation.", output)
        self.assertEqual(JsonDataManager(self.data_path).load_records(), [])

    def test_a_malformed_recipe_is_skipped_with_a_message(self):
        ai = ListAiManager([{"recipe_name": "Broken"}, make_recipe("Fine")])
        output = self.run_app(self.make_app(make_request(), None, ai_manager=ai))
        self.assertIn("Skipping 'Broken' because its recipe data is malformed.", output)
        self.assertIn("Fine (", output)

    def test_a_recipe_with_an_unreadable_quantity_is_skipped(self):
        ai = ListAiManager([make_recipe("Vague", quantity="a few"), make_recipe("Fine")])
        output = self.run_app(self.make_app(make_request(), None, ai_manager=ai))
        self.assertIn("Skipping 'Vague' because its ingredient quantities are invalid", output)
        self.assertIn("Fine (", output)

    def test_fraction_quantities_are_accepted(self):
        output = self.run_app(self.make_app(make_request(), [make_recipe(quantity="1/2")]))
        self.assertIn("Good omelette (", output)

    def test_record_ids_continue_after_existing_history(self):
        data = JsonDataManager(self.data_path)
        data.save_record({"record_id": 1})
        data.save_record({"record_id": 2})
        self.run_app(self.make_app(make_request(), [make_recipe()], data_manager=data))
        self.assertEqual([r["record_id"] for r in self.saved()], [1, 2, 3])

    def test_a_failed_save_is_reported_to_the_user(self):
        data = RejectingDataManager(self.data_path)
        output = self.run_app(self.make_app(make_request(), [make_recipe()], data_manager=data))
        self.assertIn("could not save this recipe", output)

    def test_saved_record_lists_used_and_missing_ingredients(self):
        self.run_app(self.make_app(make_request(), [make_recipe(extra=["garlic"])]))
        record = self.saved()[0]
        self.assertEqual(record["used_ingredients"], ["egg", "spinach", "cheddar"])
        self.assertEqual(record["missing_ingredients"], ["garlic"])
        self.assertEqual(record["matched_ingredients_count"], 3)
        self.assertEqual(record["cuisine"], "Western")

    def test_the_app_works_with_any_manager_that_has_the_right_methods(self):
        # polymorphism / aggregation: nothing here is a real AiManager
        ai = ListAiManager([make_recipe("Fine")])
        output = self.run_app(self.make_app(make_request(), None, ai_manager=ai))
        self.assertIn("Fine (", output)

    def test_create_default_builds_the_real_managers(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = FoodAI.RecipeApp.create_default()
        self.assertIsInstance(app, FoodAI.RecipeApp)

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

class TestRecipePresenter(unittest.TestCase):
    def test_output_goes_through_the_function_it_was_given(self):
        lines = []
        presenter = FoodAI.RecipePresenter(output=lines.append)
        presenter.show_message("hello")
        presenter.show_summary(2, 5)
        self.assertEqual(lines[0], "hello")
        self.assertIn("2 of 5 generated recipe(s) passed validation", lines[1])

class TestNoProceduralCodeRemains(unittest.TestCase):
    def test_the_module_defines_no_standalone_functions(self):
        import inspect

        functions = [
            name for name, obj in vars(FoodAI).items()
            if inspect.isfunction(obj) and obj.__module__ == FoodAI.__name__
        ]
        self.assertEqual(functions, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
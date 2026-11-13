"""
test_food_ai.py - tests for the application controller (main/recipe_app.py).

Run with:
    python -m unittest test_files.test_food_ai -v 

run whole test file folder with:
    python -m pytest test_files -v
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from decimal import Decimal
from unittest import mock
from pathlib import Path

import importlib
import inspect
import pkgutil

import FoodAI_Main_layer

from FoodAI_Main_layer.recipe_app import RecipeApp
from FoodAI_Main_layer.recipe_presenter import RecipePresenter
from FoodAI_Main_layer.recipe_translator import RecipeTranslator

from ai_layer import (
    AIProvider,
    AITransportError,
    ErrorLogger,
    RecipeValidator,
)
from ai_manager import AiManager
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
        return RecipeApp(
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
            app = RecipeApp.create_default()
        self.assertIsInstance(app, RecipeApp)

    def test_invalid_nutrition_is_unavailable_but_recipe_is_saved(self):
        invalid_values = (
            -1,
            True,
            "100",
            None,
            float("nan"),
            float("inf"),
            float("-inf"),
            10 ** 1000,
        )

        for index, value in enumerate(invalid_values):
            with self.subTest(case=index):
                recipe = make_recipe(name=f"Nutrition fallback {index}")
                recipe["nutrition"] = {
                    "basis": "whole_recipe",
                    "method": "ai_estimate",
                    "calories_kcal": value,
                    "protein_g": 40,
                    "carbohydrates_g": 50,
                    "fat_g": 26,
                }

                original_nutrition = recipe["nutrition"]
                previous_count = len(
                    JsonDataManager(self.data_path).load_records()
                )

                ai = ListAiManager([recipe])

                output = self.run_app(
                    self.make_app(
                        make_request(),
                        None,
                        ai_manager=ai,
                    )
                )

                self.assertIn(f"{recipe['recipe_name']} (", output)
                self.assertIn(
                    "Estimated nutrition: unavailable.",
                    output,
                )
                self.assertNotIn(
                    "Estimated nutrition per serving:",
                    output,
                )
                self.assertNotIn("could not save this recipe", output)

                records = JsonDataManager(self.data_path).load_records()

                self.assertEqual(len(records), previous_count + 1)

                record = records[-1]

                self.assertEqual(record["dish_name"], recipe["recipe_name"])
                self.assertEqual(
                    record["nutrition_status"],
                    "unavailable",
                )
                self.assertIsNone(record["nutrition"])
                self.assertIsNone(record["nutrition_per_serving"])
                self.assertIsNone(record["ai_response"]["nutrition"])

                self.assertEqual(
                    record["ai_response"]["ingredients"],
                    recipe["ingredients"],
                )
                self.assertEqual(
                    record["ai_response"]["instructions"],
                    recipe["instructions"],
                )

                self.assertIs(recipe["nutrition"], original_nutrition)
                self.assertIs(
                    recipe["nutrition"]["calories_kcal"],
                    value,
                )


    def test_valid_nutrition_is_displayed_saved_and_reloaded(self):
        recipe = make_recipe(name="Nutrition omelette")
        recipe["nutrition"] = {
            "basis": "whole_recipe",
            "method": "ai_estimate",
            "calories_kcal": 600,
            "protein_g": 40,
            "carbohydrates_g": 50,
            "fat_g": 26,
        }

        output = self.run_app(
            self.make_app(
                make_request(),
                [recipe],
            )
        )

        self.assertIn("Nutrition omelette (", output)
        self.assertIn("Estimated nutrition per serving:", output)
        self.assertIn("Calories: 300 kcal", output)
        self.assertIn("Protein: 20.0 g", output)
        self.assertIn("Carbohydrates: 25.0 g", output)
        self.assertIn("Fat: 13.0 g", output)
        self.assertIn(
            "Estimated nutrition based on the recipe's ingredient quantities.",
            output,
        )
        self.assertNotIn("could not save this recipe", output)

        records = JsonDataManager(self.data_path).load_records()

        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record["nutrition_status"], "estimated")
        self.assertEqual(record["nutrition"], recipe["nutrition"])
        self.assertEqual(
            record["nutrition_per_serving"],
            {
                "calories_kcal": 300,
                "protein_g": 20,
                "carbohydrates_g": 25,
                "fat_g": 13,
            },
        )
        self.assertEqual(
            record["ai_response"]["nutrition"],
            record["nutrition"],
        )


    def test_missing_nutrition_does_not_prevent_application_save(self):
        recipe = make_recipe(name="No nutrition omelette")
        ai = ListAiManager([recipe])

        output = self.run_app(
            self.make_app(
                make_request(),
                None,
                ai_manager=ai,
            )
        )

        self.assertIn("No nutrition omelette (", output)
        self.assertIn("Estimated nutrition: unavailable.", output)
        self.assertNotIn("could not save this recipe", output)

        records = JsonDataManager(self.data_path).load_records()

        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record["nutrition_status"], "unavailable")
        self.assertIsNone(record["nutrition"])
        self.assertIsNone(record["nutrition_per_serving"])
        self.assertIsNone(record["ai_response"]["nutrition"])

        self.assertNotIn("nutrition", recipe)

class TestRecipeTranslator(unittest.TestCase):
    def setUp(self):
        self.translator = RecipeTranslator()

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
        presenter = RecipePresenter(output=lines.append)
        presenter.show_message("hello")
        presenter.show_summary(2, 5)
        self.assertEqual(lines[0], "hello")
        self.assertIn("2 of 5 generated recipe(s) passed validation", lines[1])

    def test_terminal_control_characters_are_escaped(self):
        lines = []
        presenter = RecipePresenter(output=lines.append)

        presenter.show_message(
            "Recipe\x1b[2J\rhidden\b\x9b31m"
        )

        self.assertEqual(
            lines,
            ["Recipe\\x1b[2J\\x0dhidden\\x08\\x9b31m"],
        )


    def test_normal_text_newlines_and_tabs_are_preserved(self):
        lines = []
        presenter = RecipePresenter(output=lines.append)

        message = "Chicken sauté\n\tProtein: 20 g"

        presenter.show_message(message)

        self.assertEqual(lines, [message])

class TestNoProceduralCodeRemains(unittest.TestCase):
    def test_no_module_in_the_package_defines_standalone_functions(self):
        functions = []

        for info in pkgutil.iter_modules(FoodAI_Main_layer.__path__):
            module = importlib.import_module(
                f"{FoodAI_Main_layer.__name__}.{info.name}")
            functions += [
                f"{module.__name__}.{name}"
                for name, obj in vars(module).items()
                if inspect.isfunction(obj)
                and obj.__module__ == module.__name__]

        self.assertEqual(functions, [])

class TestJsonDataManager(unittest.TestCase):
    """Tests real JSON persistence using isolated temporary files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.json"

    def write_history(self, content):
        self.path.write_text(content, encoding="utf-8")

    def read_history(self):
        return self.path.read_text(encoding="utf-8")

    def test_missing_history_is_initialised_as_empty_list(self):
        self.assertFalse(self.path.exists())

        manager = JsonDataManager(str(self.path))

        self.assertTrue(self.path.exists())
        self.assertEqual(manager.load_records(), [])
        self.assertEqual(json.loads(self.read_history()), [])

    def test_deleted_history_is_recreated_when_loaded(self):
        manager = JsonDataManager(str(self.path))
        self.path.unlink()

        self.assertEqual(manager.load_records(), [])
        self.assertTrue(self.path.exists())
        self.assertEqual(json.loads(self.read_history()), [])

    def test_empty_history_file_is_handled(self):
        self.write_history("")

        manager = JsonDataManager(str(self.path))

        self.assertEqual(manager.load_records(), [])
        self.assertTrue(manager.save_record({"record_id": 1}))
        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}],
        )

    def test_corrupt_json_loads_without_crashing(self):
        original = '{"record_id": broken'
        self.write_history(original)

        manager = JsonDataManager(str(self.path))

        self.assertEqual(manager.load_records(), [])
        self.assertEqual(self.read_history(), original)

    def test_save_does_not_overwrite_corrupt_history(self):
        original = '{"record_id": broken'
        self.write_history(original)
        manager = JsonDataManager(str(self.path))

        saved = manager.save_record({"record_id": 1})

        self.assertFalse(saved)
        self.assertEqual(self.read_history(), original)

    def test_invalid_history_structures_are_not_overwritten(self):
        invalid_histories = (
            '{"record_id": 1}',
            '[{"record_id": 1}, "invalid record"]',
            "null",
        )

        for original in invalid_histories:
            with self.subTest(history=original):
                self.write_history(original)
                manager = JsonDataManager(str(self.path))

                self.assertEqual(manager.load_records(), [])
                self.assertFalse(
                    manager.save_record({"record_id": 2})
                )
                self.assertEqual(self.read_history(), original)

    def test_records_are_available_to_a_new_manager_instance(self):
        first = JsonDataManager(str(self.path))
        record = {
            "record_id": 1,
            "dish_name": "Omelette",
            "used_ingredients": ["egg"],
            "cooking_time_mins": 12,
        }

        self.assertTrue(first.save_record(record))

        second = JsonDataManager(str(self.path))

        self.assertEqual(second.load_records(), [record])

    def test_saving_a_second_record_preserves_the_first(self):
        manager = JsonDataManager(str(self.path))

        self.assertTrue(manager.save_record({"record_id": 1}))
        self.assertTrue(manager.save_record({"record_id": 2}))

        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}, {"record_id": 2}],
        )

    def test_invalid_record_type_does_not_change_history(self):
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))
        original = self.read_history()

        self.assertFalse(
            manager.save_record(["not", "a", "dict"])
        )
        self.assertEqual(self.read_history(), original)

    def test_unserialisable_record_does_not_change_history(self):
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))
        original = self.read_history()

        saved = manager.save_record(
            {
                "record_id": 2,
                "invalid_value": object(),
            }
        )

        self.assertFalse(saved)
        self.assertEqual(self.read_history(), original)

    def test_non_finite_number_does_not_change_history(self):
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))
        original = self.read_history()

        saved = manager.save_record(
            {
                "record_id": 2,
                "amount": float("nan"),
            }
        )

        self.assertFalse(saved)
        self.assertEqual(self.read_history(), original)

    def test_read_permission_error_is_handled(self):
        manager = JsonDataManager(str(self.path))

        with mock.patch(
            "builtins.open",
            side_effect=PermissionError("Access denied"),
        ):
            self.assertEqual(manager.load_records(), [])

    def test_storage_creation_failure_is_handled(self):
        missing_parent = (
            Path(self.tmp.name) / "missing" / "history.json"
        )

        manager = JsonDataManager(str(missing_parent))

        self.assertFalse(manager.init_storage())
        self.assertEqual(manager.load_records(), [])
        self.assertFalse(
            manager.save_record({"record_id": 1})
        )

    def test_query_by_ingredient_is_case_insensitive(self):
        manager = JsonDataManager(str(self.path))
        egg_recipe = {
            "record_id": 1,
            "used_ingredients": ["egg", "spinach"],
        }
        rice_recipe = {
            "record_id": 2,
            "used_ingredients": ["rice"],
        }

        self.assertTrue(manager.save_record(egg_recipe))
        self.assertTrue(manager.save_record(rice_recipe))

        self.assertEqual(
            manager.query_by_ingredient(" EGG "),
            [egg_recipe],
        )

    def test_query_by_max_time_includes_the_boundary(self):
        manager = JsonDataManager(str(self.path))
        quick = {
            "record_id": 1,
            "cooking_time_mins": 10,
        }
        boundary = {
            "record_id": 2,
            "cooking_time_mins": 30,
        }
        slow = {
            "record_id": 3,
            "cooking_time_mins": 45,
        }

        for record in (quick, boundary, slow):
            self.assertTrue(manager.save_record(record))

        self.assertEqual(
            manager.query_by_max_time(30),
            [quick, boundary],
        )

    def test_refused_replacement_falls_back_to_writing_in_place(self):
        # Docker cannot replace a single mounted file ("Device or resource
        # busy"), so the new record must still be saved by writing over it.
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))

        with mock.patch(
            "data_manager.os.replace",
            side_effect=PermissionError("Replacement denied"),
        ):
            saved = manager.save_record({"record_id": 2})

        self.assertTrue(saved)
        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}, {"record_id": 2}],
        )
        self.assertEqual(
            list(self.path.parent.glob(".recipes-history-*.tmp")),
            [],
        )

    def test_normal_save_does_not_use_the_in_place_fallback(self):
        manager = JsonDataManager(str(self.path))

        with mock.patch.object(
            JsonDataManager, "_write_in_place"
        ) as fallback:
            self.assertTrue(manager.save_record({"record_id": 1}))

        fallback.assert_not_called()

    def test_failed_replacement_and_fallback_preserve_existing_history(self):
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))

        original = self.read_history()

        with mock.patch(
            "data_manager.os.replace",
            side_effect=PermissionError("Replacement denied"),
        ), mock.patch.object(
            JsonDataManager,
            "_write_in_place",
            side_effect=OSError("Read-only file system"),
        ):
            saved = manager.save_record({"record_id": 2})

        self.assertFalse(saved)
        self.assertEqual(self.read_history(), original)
        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}],
        )
        self.assertEqual(
            list(self.path.parent.glob(".recipes-history-*.tmp")),
            [],
        )


    def test_failed_temporary_write_preserves_existing_history(self):
        manager = JsonDataManager(str(self.path))
        self.assertTrue(manager.save_record({"record_id": 1}))

        original = self.read_history()

        with mock.patch(
            "data_manager.os.fsync",
            side_effect=OSError("Disk synchronization failed"),
        ):
            saved = manager.save_record({"record_id": 2})

        self.assertFalse(saved)
        self.assertEqual(self.read_history(), original)
        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}],
        )
        self.assertEqual(
            list(self.path.parent.glob(".recipes-history-*.tmp")),
            [],
        )


    def test_successful_save_leaves_no_temporary_files(self):
        manager = JsonDataManager(str(self.path))

        self.assertTrue(manager.save_record({"record_id": 1}))
        self.assertTrue(manager.save_record({"record_id": 2}))

        self.assertEqual(
            manager.load_records(),
            [{"record_id": 1}, {"record_id": 2}],
        )
        self.assertEqual(
            list(self.path.parent.glob(".recipes-history-*.tmp")),
            [],
        )

class TestManualValidationTranslator(unittest.TestCase):
    """Checks that custom exclusions reach the logic manager."""

    def test_custom_exclusions_are_passed_to_logic_preferences(self):
        request = make_request("peanut")
        translator = RecipeTranslator()

        preferences = translator.to_logic_preferences(
            request,
            ["peanut"],
        )

        self.assertEqual(
            preferences["custom_exclusions"],
            ["peanut"],
        )

    def test_no_custom_exclusions_produces_an_empty_list(self):
        request = make_request("none")
        translator = RecipeTranslator()

        preferences = translator.to_logic_preferences(request, [])

        self.assertEqual(preferences["custom_exclusions"], [])


class TestManualValidationAppFlow(AppTestCase):
    """Checks manual-validation display, counting, and persistence."""

    def test_pending_checks_are_displayed_and_saved(self):
        recipe = make_recipe(
            name="Pending omelette",
            extra=["special sauce"],
        )

        output = self.run_app(
            self.make_app(
                make_request("peanut"),
                [recipe],
            )
        )

        self.assertIn("Pending omelette (", output)
        self.assertIn("Manual validation:", output)
        self.assertIn("PENDING", output)
        self.assertIn(
            "special sauce: check for peanut",
            output,
        )
        self.assertIn(
            "1 displayed recipe(s) require manual validation",
            output,
        )
        self.assertIn(
            "not confirmed suitable for your exclusions",
            output,
        )

        records = self.saved()
        self.assertEqual(len(records), 1)

        record = records[0]
        self.assertEqual(
            record["validation_state"],
            "pending_manual_validation",
        )
        self.assertEqual(len(record["manual_validation"]), 1)

        entry = record["manual_validation"][0]
        self.assertEqual(entry["ingredient"], "special sauce")
        self.assertEqual(
            entry["exclusions_to_check"],
            ["peanut"],
        )
        self.assertEqual(entry["status"], "pending")
        self.assertTrue(entry["reason"])

        reloaded = JsonDataManager(self.data_path).load_records()

        self.assertEqual(
            reloaded[0]["manual_validation"],
            record["manual_validation"],
        )
        self.assertEqual(
            reloaded[0]["validation_state"],
            "pending_manual_validation",
        )

    def test_clear_recipe_has_no_manual_validation_section(self):
        output = self.run_app(
            self.make_app(
                make_request("peanut"),
                [make_recipe()],
            )
        )

        self.assertIn("Good omelette (", output)
        self.assertNotIn("Manual validation:", output)
        self.assertNotIn("require manual validation", output)

        record = self.saved()[0]
        self.assertEqual(record["manual_validation"], [])
        self.assertEqual(
            record["validation_state"],
            "automated_checks_passed",
        )

    def test_vague_ingredient_without_exclusions_is_not_pending(self):
        recipe = make_recipe(
            name="No exclusions",
            extra=["special sauce"],
        )

        output = self.run_app(
            self.make_app(
                make_request("none"),
                [recipe],
            )
        )

        self.assertIn("No exclusions (", output)
        self.assertNotIn("Manual validation:", output)

        record = self.saved()[0]
        self.assertEqual(record["manual_validation"], [])
        self.assertEqual(
            record["validation_state"],
            "automated_checks_passed",
        )

    def test_vague_seasoning_is_displayed_and_saved(self):
        recipe = make_recipe(name="Seasoned omelette")
        recipe["seasonings"] = ["salt", "special seasoning"]

        output = self.run_app(
            self.make_app(
                make_request("peanut"),
                [recipe],
            )
        )

        self.assertIn(
            "special seasoning: check for peanut",
            output,
        )

        record = self.saved()[0]

        self.assertEqual(
            record["validation_state"],
            "pending_manual_validation",
        )
        self.assertEqual(
            [
                entry["ingredient"]
                for entry in record["manual_validation"]
            ],
            ["special seasoning"],
        )

    def test_pending_count_counts_recipes_not_individual_checks(self):
        pending = make_recipe(
            name="Pending",
            extra=["special sauce", "signature dressing"],
        )
        clear = make_recipe(name="Clear")

        output = self.run_app(
            self.make_app(
                make_request("peanut"),
                [pending, clear],
            )
        )

        self.assertIn(
            "1 displayed recipe(s) require manual validation",
            output,
        )

        records = self.saved()
        self.assertEqual(len(records), 2)

        pending_record = next(
            record
            for record in records
            if record["dish_name"] == "Pending"
        )
        clear_record = next(
            record
            for record in records
            if record["dish_name"] == "Clear"
        )

        self.assertEqual(
            len(pending_record["manual_validation"]),
            2,
        )
        self.assertEqual(
            {
                entry["ingredient"]
                for entry in pending_record["manual_validation"]
            },
            {"special sauce", "signature dressing"},
        )
        self.assertEqual(
            pending_record["validation_state"],
            "pending_manual_validation",
        )

        self.assertEqual(
            clear_record["manual_validation"],
            [],
        )
        self.assertEqual(
            clear_record["validation_state"],
            "automated_checks_passed",
        )

    def test_known_conflict_is_not_displayed_or_saved_as_pending(self):
        recipe = make_recipe(
            name="Rejected omelette",
            extra=["special sauce", "peanut butter"],
        )

        output = self.run_app(
            self.make_app(
                make_request("peanut"),
                [recipe],
            )
        )

        self.assertIn("No recipes passed validation.", output)
        self.assertNotIn("Rejected omelette (", output)
        self.assertNotIn(
            "displayed recipe(s) require manual validation",
            output,
        )
        self.assertEqual(
            JsonDataManager(self.data_path).load_records(),
            [],
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
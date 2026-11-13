import os
import tempfile
import unittest
from copy import deepcopy
from types import SimpleNamespace

from ai_layer.recipe_prompt_builder import RecipePromptBuilder
from ai_layer.recipe_schema import RECIPE_RESPONSE_SCHEMA
from ai_layer.nutrition_estimate import NutritionEstimate
from FoodAI_Main_layer.recipe_presenter import RecipePresenter
from FoodAI_Main_layer.recipe_translator import RecipeTranslator
from data_manager import JsonDataManager


INVALID_NUTRIENT_VALUES = [-1, True, "100", None, float("nan"), float("inf")]
INVALID_SERVINGS = [0, -1, True, "2", None, float("nan"), float("inf")]
VALID_VALUES = {
    "calories_kcal": 600,
    "protein_g": 40,
    "carbohydrates_g": 50,
    "fat_g": 26,
}
PER_SERVING = {
    "calories_kcal": 300,
    "protein_g": 20,
    "carbohydrates_g": 25,
    "fat_g": 13,
}


def render_recipe(recipe, manual_validation=None, warning=None, saved=True):
    output = []
    evaluation = SimpleNamespace(
        manual_validation=manual_validation or [],
        warning=warning,
    )

    RecipePresenter(output=output.append).show_recipe(
        recipe, evaluation, saved=saved
    )

    return "\n".join(output)


class NutritionTestCase(unittest.TestCase):
    """Shared helpers (these replace the old pytest fixtures and helpers)."""

    @staticmethod
    def make_recipe():
        # A new dictionary on every call, so tests never share state.
        return {
            "recipe_name": "Nutrition test recipe",
            "description": "A recipe used for testing nutrition display.",
            "estimated_cooking_time_minutes": 10,
            "servings": 2,
            "is_breakfast": False,
            "ingredients": [{"name": "rice", "quantity": "100", "unit": "g"}],
            "seasonings": [],
            "instructions": ["Cook the rice."],
            "nutrition": {
                "basis": "whole_recipe",
                "method": "ai_estimate",
                **VALID_VALUES,
            },
        }

    def make_history_path(self):
        # A new temporary folder per call; removed automatically afterwards.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return os.path.join(folder.name, "recipes_history.json")

    def assertNutritionUnavailable(self, text):
        self.assertIn("Estimated nutrition: unavailable.", text)
        self.assertNotIn("Estimated nutrition per serving:", text)

    def assertRecordUnavailable(self, record):
        self.assertEqual(record["nutrition_status"], "unavailable")
        self.assertIsNone(record["nutrition"])
        self.assertIsNone(record["nutrition_per_serving"])


class TestNutritionEstimate(NutritionTestCase):
    def test_whole_recipe_estimate_is_validated(self):
        recipe = self.make_recipe()

        estimate = NutritionEstimate.from_recipe(recipe)

        self.assertIsNotNone(estimate)
        self.assertEqual(estimate.to_dict(), recipe["nutrition"])

    def test_per_serving_values_are_calculated(self):
        estimate = NutritionEstimate.from_recipe(self.make_recipe())

        self.assertEqual(estimate.per_serving(2), PER_SERVING)

    def test_invalid_nutrient_values_are_unavailable(self):
        for value in INVALID_NUTRIENT_VALUES:
            with self.subTest(value=value):
                recipe = self.make_recipe()
                recipe["nutrition"]["protein_g"] = value

                self.assertIsNone(NutritionEstimate.from_recipe(recipe))

    def test_invalid_servings_are_unavailable(self):
        for servings in INVALID_SERVINGS:
            with self.subTest(servings=servings):
                estimate = NutritionEstimate.from_recipe(self.make_recipe())

                self.assertIsNone(estimate.per_serving(servings))

    def test_missing_nutrition_is_supported(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]

        self.assertIsNone(NutritionEstimate.from_recipe(recipe))

    def test_missing_nutrient_is_unavailable(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]["fat_g"]

        self.assertIsNone(NutritionEstimate.from_recipe(recipe))

    def test_incorrect_metadata_is_unavailable(self):
        for field, value in [("basis", "per_serving"), ("method", "verified")]:
            with self.subTest(field=field, value=value):
                recipe = self.make_recipe()
                recipe["nutrition"][field] = value

                self.assertIsNone(NutritionEstimate.from_recipe(recipe))

    def test_analysis_does_not_modify_original_recipe(self):
        recipe = self.make_recipe()
        original = deepcopy(recipe)

        estimate = NutritionEstimate.from_recipe(recipe)
        estimate.per_serving(2)

        self.assertEqual(recipe, original)

    def test_zero_nutrient_value_is_allowed(self):
        recipe = self.make_recipe()
        recipe["nutrition"]["fat_g"] = 0

        estimate = NutritionEstimate.from_recipe(recipe)

        self.assertIsNotNone(estimate)
        self.assertEqual(estimate.fat_g, 0)

    def test_non_dictionary_recipe_is_unavailable(self):
        for value in [None, [], "invalid"]:
            with self.subTest(value=value):
                self.assertIsNone(NutritionEstimate.from_recipe(value))

    def test_direct_construction_rejects_invalid_values(self):
        values = [*INVALID_NUTRIENT_VALUES, float("-inf"), 10 ** 1000]

        for field in NutritionEstimate.FIELDS:
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field):
                        NutritionEstimate(**{**VALID_VALUES, field: value})

    def test_direct_construction_accepts_valid_values(self):
        estimate = NutritionEstimate(**VALID_VALUES)

        self.assertEqual(estimate.per_serving(2), PER_SERVING)

    def test_direct_construction_accepts_zero_values(self):
        zeros = dict.fromkeys(NutritionEstimate.FIELDS, 0)

        self.assertEqual(NutritionEstimate(**zeros).per_serving(2), zeros)


class TestNutritionPrompt(NutritionTestCase):
    def setUp(self):
        self.prompt = RecipePromptBuilder().build({})

    def test_prompt_requests_whole_recipe_nutrition(self):
        self.assertIn("WHOLE recipe", self.prompt)
        self.assertIn(
            "all servings combined, not one serving", self.prompt
        )

    def test_prompt_requests_all_nutrition_fields(self):
        for field in NutritionEstimate.FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, self.prompt)

    def test_prompt_identifies_estimation_method(self):
        self.assertIn("whole_recipe", self.prompt)
        self.assertIn("ai_estimate", self.prompt)
        self.assertIn("not verified nutritional measurements", self.prompt)


class TestNutritionSchema(NutritionTestCase):
    def setUp(self):
        self.nutrition_schema = (
            RECIPE_RESPONSE_SCHEMA["items"]["properties"]["nutrition"]
        )

    def test_recipe_schema_requires_nutrition(self):
        recipe_schema = RECIPE_RESPONSE_SCHEMA["items"]

        self.assertIn("nutrition", recipe_schema["properties"])
        self.assertIn("nutrition", recipe_schema["required"])

    def test_nutrition_schema_requires_numeric_nutrients(self):
        schema = self.nutrition_schema

        self.assertEqual(schema["type"], "OBJECT")

        for field in NutritionEstimate.FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, schema["required"])
                self.assertEqual(
                    schema["properties"][field]["type"], "NUMBER"
                )

    def test_nutrition_schema_requires_whole_recipe_basis(self):
        schema = self.nutrition_schema

        self.assertIn("basis", schema["required"])
        self.assertEqual(
            schema["properties"]["basis"],
            {
                "type": "STRING",
                "enum": ["whole_recipe"],
            },
        )

    def test_nutrition_schema_requires_ai_estimate_method(self):
        schema = self.nutrition_schema

        self.assertIn("method", schema["required"])
        self.assertEqual(
            schema["properties"]["method"],
            {
                "type": "STRING",
                "enum": ["ai_estimate"],
            },
        )


class TestNutritionPresenter(NutritionTestCase):
    def test_displays_nutrition_per_serving(self):
        text = render_recipe(self.make_recipe())

        self.assertIn("Estimated nutrition per serving:", text)
        self.assertIn("Calories: 300 kcal", text)
        self.assertIn("Protein: 20.0 g", text)
        self.assertIn("Carbohydrates: 25.0 g", text)
        self.assertIn("Fat: 13.0 g", text)

    def test_displays_estimate_label(self):
        self.assertIn(
            "Estimated nutrition per serving:",
            render_recipe(self.make_recipe()),
        )

    def test_missing_nutrition_displays_unavailable(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]

        text = render_recipe(recipe)

        self.assertNutritionUnavailable(text)
        self.assertIn(recipe["recipe_name"], text)

    def test_missing_nutrient_displays_unavailable(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]["protein_g"]

        text = render_recipe(recipe)

        self.assertIn("Estimated nutrition: unavailable.", text)
        self.assertNotIn("Calories:", text)

    def test_invalid_nutrition_displays_unavailable(self):
        for value in INVALID_NUTRIENT_VALUES:
            with self.subTest(value=value):
                recipe = self.make_recipe()
                recipe["nutrition"]["calories_kcal"] = value

                self.assertNutritionUnavailable(render_recipe(recipe))

    def test_invalid_servings_displays_unavailable(self):
        for servings in INVALID_SERVINGS:
            with self.subTest(servings=servings):
                recipe = self.make_recipe()
                recipe["servings"] = servings

                self.assertNutritionUnavailable(render_recipe(recipe))

    def test_missing_servings_displays_unavailable(self):
        recipe = self.make_recipe()
        del recipe["servings"]

        self.assertNutritionUnavailable(render_recipe(recipe))

    def test_nutrition_is_displayed_once_with_manual_validation(self):
        manual_validation = [
            {
                "ingredient": "special sauce",
                "exclusions_to_check": ["peanut"],
                "reason": "The sauce composition needs checking.",
            },
            {
                "ingredient": "signature dressing",
                "exclusions_to_check": ["peanut"],
                "reason": "The dressing composition needs checking.",
            },
        ]

        text = render_recipe(
            self.make_recipe(), manual_validation=manual_validation
        )

        self.assertIn("Manual validation:", text)
        self.assertIn("special sauce: check for peanut", text)
        self.assertIn("signature dressing: check for peanut", text)
        self.assertEqual(
            text.count("Estimated nutrition per serving:"), 1
        )

    def test_warning_and_save_failure_are_still_displayed(self):
        text = render_recipe(
            self.make_recipe(), warning="Test recipe warning.", saved=False
        )

        self.assertIn("Estimated nutrition per serving:", text)
        self.assertIn("Note: Test recipe warning.", text)
        self.assertIn(
            "could not save this recipe to recipes_history.json", text
        )


class TestNutritionPersistence(NutritionTestCase):
    @staticmethod
    def make_record(recipe):
        return RecipeTranslator().to_record(
            record_id=1,
            recipe=recipe,
            req={
                "ingredients": [
                    {"name": "rice", "quantity": "100", "unit": "g"},
                ],
            },
            ai_input={
                "cuisine": "Any",
                "meal_type": "Any",
                "taste_preference": "Any",
                "dietary_restrictions": [],
            },
        )

    def test_record_contains_validated_nutrition(self):
        recipe = self.make_recipe()

        record = self.make_record(recipe)

        self.assertEqual(record["nutrition_status"], "estimated")
        self.assertEqual(record["nutrition"], recipe["nutrition"])
        self.assertEqual(record["nutrition_per_serving"], PER_SERVING)

    def test_missing_nutrition_is_saved_as_unavailable(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]

        record = self.make_record(recipe)

        self.assertEqual(record["dish_name"], recipe["recipe_name"])
        self.assertRecordUnavailable(record)

    def test_missing_nutrient_is_saved_as_unavailable(self):
        recipe = self.make_recipe()
        del recipe["nutrition"]["protein_g"]

        self.assertRecordUnavailable(self.make_record(recipe))

    def test_invalid_nutrition_does_not_prevent_saving(self):
        for value in INVALID_NUTRIENT_VALUES:
            with self.subTest(value=value):
                recipe = self.make_recipe()
                history_path = self.make_history_path()
                recipe["nutrition"]["calories_kcal"] = value

                record = self.make_record(recipe)
                manager = JsonDataManager(file_path=history_path)

                self.assertRecordUnavailable(record)
                self.assertIs(manager.save_record(record), True)

                reloaded = JsonDataManager(
                    file_path=history_path
                ).load_records()

                self.assertEqual(reloaded, [record])

    def test_invalid_servings_make_nutrition_unavailable(self):
        for servings in INVALID_SERVINGS:
            with self.subTest(servings=servings):
                recipe = self.make_recipe()
                recipe["servings"] = servings

                self.assertRecordUnavailable(self.make_record(recipe))

    def test_valid_nutrition_survives_save_and_reload(self):
        recipe = self.make_recipe()
        history_path = self.make_history_path()
        record = self.make_record(recipe)
        manager = JsonDataManager(file_path=history_path)

        self.assertIs(manager.save_record(record), True)

        reloaded = JsonDataManager(file_path=history_path).load_records()

        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0]["nutrition"], record["nutrition"])
        self.assertEqual(
            reloaded[0]["nutrition_per_serving"],
            record["nutrition_per_serving"],
        )
        self.assertEqual(reloaded[0]["nutrition_status"], "estimated")

    def test_older_record_without_nutrition_can_still_load(self):
        history_path = self.make_history_path()
        manager = JsonDataManager(file_path=history_path)

        old_record = {
            "record_id": 1,
            "dish_name": "Older saved recipe",
            "servings": 2,
            "used_ingredients": ["rice"],
            "cooking_time_mins": 10,
        }

        self.assertIs(manager.save_record(old_record), True)

        reloaded = JsonDataManager(file_path=history_path).load_records()

        self.assertEqual(reloaded, [old_record])
        self.assertNotIn("nutrition", reloaded[0])

    def test_displayed_values_match_saved_values(self):
        recipe = self.make_recipe()
        record = self.make_record(recipe)
        text = render_recipe(recipe)
        values = record["nutrition_per_serving"]

        self.assertIn(f"Calories: {values['calories_kcal']:.0f} kcal", text)
        self.assertIn(f"Protein: {values['protein_g']:.1f} g", text)
        self.assertIn(f"Carbohydrates: {values['carbohydrates_g']:.1f} g", text)
        self.assertIn(f"Fat: {values['fat_g']:.1f} g", text)

    def test_display_labels_estimate_and_record_saves_ai_method(self):
        recipe = self.make_recipe()
        record = self.make_record(recipe)
        text = render_recipe(recipe)

        self.assertEqual(record["nutrition"]["method"], "ai_estimate")
        self.assertIn("Estimated nutrition per serving:", text)
        self.assertIn(
            "Estimated nutrition based on the recipe's ingredient quantities.",
            text,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
from copy import deepcopy
import pytest
from ai_layer.recipe_prompt_builder import RecipePromptBuilder
from ai_layer.recipe_schema import RECIPE_RESPONSE_SCHEMA
from ai_layer.nutrition_estimate import NutritionEstimate
from types import SimpleNamespace
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


@pytest.fixture
def recipe():
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


@pytest.fixture
def prompt():
    return RecipePromptBuilder().build({})


@pytest.fixture
def nutrition_schema():
    return RECIPE_RESPONSE_SCHEMA["items"]["properties"]["nutrition"]


@pytest.fixture
def history_path(tmp_path):
    return str(tmp_path / "recipes_history.json")


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


def assert_nutrition_unavailable(text):
    assert "Estimated nutrition: unavailable." in text
    assert "Estimated nutrition per serving:" not in text


def assert_record_unavailable(record):
    assert record["nutrition_status"] == "unavailable"
    assert record["nutrition"] is None
    assert record["nutrition_per_serving"] is None


class TestNutritionEstimate:
    def test_whole_recipe_estimate_is_validated(self, recipe):
        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate is not None
        assert estimate.to_dict() == recipe["nutrition"]

    def test_per_serving_values_are_calculated(self, recipe):
        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate.per_serving(2) == PER_SERVING

    @pytest.mark.parametrize("value", INVALID_NUTRIENT_VALUES)
    def test_invalid_nutrient_values_are_unavailable(self, recipe, value):
        recipe["nutrition"]["protein_g"] = value

        assert NutritionEstimate.from_recipe(recipe) is None

    @pytest.mark.parametrize("servings", INVALID_SERVINGS)
    def test_invalid_servings_are_unavailable(self, recipe, servings):
        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate.per_serving(servings) is None

    def test_missing_nutrition_is_supported(self, recipe):
        del recipe["nutrition"]

        assert NutritionEstimate.from_recipe(recipe) is None

    def test_missing_nutrient_is_unavailable(self, recipe):
        del recipe["nutrition"]["fat_g"]

        assert NutritionEstimate.from_recipe(recipe) is None

    @pytest.mark.parametrize(
        ("field", "value"),
        [("basis", "per_serving"), ("method", "verified")],
    )
    def test_incorrect_metadata_is_unavailable(self, recipe, field, value):
        recipe["nutrition"][field] = value

        assert NutritionEstimate.from_recipe(recipe) is None

    def test_analysis_does_not_modify_original_recipe(self, recipe):
        original = deepcopy(recipe)

        estimate = NutritionEstimate.from_recipe(recipe)
        estimate.per_serving(2)

        assert recipe == original

    def test_zero_nutrient_value_is_allowed(self, recipe):
        recipe["nutrition"]["fat_g"] = 0

        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate is not None
        assert estimate.fat_g == 0

    @pytest.mark.parametrize("value", [None, [], "invalid"])
    def test_non_dictionary_recipe_is_unavailable(self, value):
        assert NutritionEstimate.from_recipe(value) is None

    @pytest.mark.parametrize("field", NutritionEstimate.FIELDS)
    @pytest.mark.parametrize(
        "value",
        [*INVALID_NUTRIENT_VALUES, float("-inf"), 10 ** 1000],
    )
    def test_direct_construction_rejects_invalid_values(self, field, value):
        with pytest.raises(ValueError, match=field):
            NutritionEstimate(**{**VALID_VALUES, field: value})

    def test_direct_construction_accepts_valid_values(self):
        estimate = NutritionEstimate(**VALID_VALUES)

        assert estimate.per_serving(2) == PER_SERVING

    def test_direct_construction_accepts_zero_values(self):
        zeros = dict.fromkeys(NutritionEstimate.FIELDS, 0)

        assert NutritionEstimate(**zeros).per_serving(2) == zeros


class TestNutritionPrompt:
    def test_prompt_requests_whole_recipe_nutrition(self, prompt):
        assert "WHOLE recipe" in prompt
        assert "all servings combined, not one serving" in prompt

    def test_prompt_requests_all_nutrition_fields(self, prompt):
        for field in NutritionEstimate.FIELDS:
            assert field in prompt

    def test_prompt_identifies_estimation_method(self, prompt):
        assert "whole_recipe" in prompt
        assert "ai_estimate" in prompt
        assert "not verified nutritional measurements" in prompt


class TestNutritionSchema:
    def test_recipe_schema_requires_nutrition(self):
        recipe_schema = RECIPE_RESPONSE_SCHEMA["items"]

        assert "nutrition" in recipe_schema["properties"]
        assert "nutrition" in recipe_schema["required"]

    def test_nutrition_schema_requires_numeric_nutrients(
        self, nutrition_schema
    ):
        assert nutrition_schema["type"] == "OBJECT"

        for field in NutritionEstimate.FIELDS:
            assert field in nutrition_schema["required"]
            assert nutrition_schema["properties"][field]["type"] == "NUMBER"

    def test_nutrition_schema_requires_whole_recipe_basis(
        self, nutrition_schema
    ):
        assert "basis" in nutrition_schema["required"]
        assert nutrition_schema["properties"]["basis"] == {
            "type": "STRING",
            "enum": ["whole_recipe"],
        }

    def test_nutrition_schema_requires_ai_estimate_method(
        self, nutrition_schema
    ):
        assert "method" in nutrition_schema["required"]
        assert nutrition_schema["properties"]["method"] == {
            "type": "STRING",
            "enum": ["ai_estimate"],
        }


class TestNutritionPresenter:
    def test_displays_nutrition_per_serving(self, recipe):
        text = render_recipe(recipe)

        assert "Estimated nutrition per serving:" in text
        assert "Calories: 300 kcal" in text
        assert "Protein: 20.0 g" in text
        assert "Carbohydrates: 25.0 g" in text
        assert "Fat: 13.0 g" in text

    def test_displays_estimate_label(self, recipe):
        assert "Estimated nutrition per serving:" in render_recipe(recipe)

    def test_missing_nutrition_displays_unavailable(self, recipe):
        del recipe["nutrition"]

        text = render_recipe(recipe)

        assert_nutrition_unavailable(text)
        assert recipe["recipe_name"] in text

    def test_missing_nutrient_displays_unavailable(self, recipe):
        del recipe["nutrition"]["protein_g"]

        text = render_recipe(recipe)

        assert "Estimated nutrition: unavailable." in text
        assert "Calories:" not in text

    @pytest.mark.parametrize("value", INVALID_NUTRIENT_VALUES)
    def test_invalid_nutrition_displays_unavailable(self, recipe, value):
        recipe["nutrition"]["calories_kcal"] = value

        assert_nutrition_unavailable(render_recipe(recipe))

    @pytest.mark.parametrize("servings", INVALID_SERVINGS)
    def test_invalid_servings_displays_unavailable(self, recipe, servings):
        recipe["servings"] = servings

        assert_nutrition_unavailable(render_recipe(recipe))

    def test_missing_servings_displays_unavailable(self, recipe):
        del recipe["servings"]

        assert_nutrition_unavailable(render_recipe(recipe))

    def test_nutrition_is_displayed_once_with_manual_validation(self, recipe):
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

        text = render_recipe(recipe, manual_validation=manual_validation)

        assert "Manual validation:" in text
        assert "special sauce: check for peanut" in text
        assert "signature dressing: check for peanut" in text
        assert text.count("Estimated nutrition per serving:") == 1

    def test_warning_and_save_failure_are_still_displayed(self, recipe):
        text = render_recipe(
            recipe, warning="Test recipe warning.", saved=False
        )

        assert "Estimated nutrition per serving:" in text
        assert "Note: Test recipe warning." in text
        assert "could not save this recipe to recipes_history.json" in text


class TestNutritionPersistence:
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

    def test_record_contains_validated_nutrition(self, recipe):
        record = self.make_record(recipe)

        assert record["nutrition_status"] == "estimated"
        assert record["nutrition"] == recipe["nutrition"]
        assert record["nutrition_per_serving"] == PER_SERVING

    def test_missing_nutrition_is_saved_as_unavailable(self, recipe):
        del recipe["nutrition"]

        record = self.make_record(recipe)

        assert record["dish_name"] == recipe["recipe_name"]
        assert_record_unavailable(record)

    def test_missing_nutrient_is_saved_as_unavailable(self, recipe):
        del recipe["nutrition"]["protein_g"]

        assert_record_unavailable(self.make_record(recipe))

    @pytest.mark.parametrize("value", INVALID_NUTRIENT_VALUES)
    def test_invalid_nutrition_does_not_prevent_saving(
        self, recipe, value, history_path
    ):
        recipe["nutrition"]["calories_kcal"] = value

        record = self.make_record(recipe)
        manager = JsonDataManager(file_path=history_path)

        assert_record_unavailable(record)
        assert manager.save_record(record) is True

        reloaded = JsonDataManager(file_path=history_path).load_records()

        assert reloaded == [record]

    @pytest.mark.parametrize("servings", INVALID_SERVINGS)
    def test_invalid_servings_make_nutrition_unavailable(
        self, recipe, servings
    ):
        recipe["servings"] = servings

        assert_record_unavailable(self.make_record(recipe))

    def test_valid_nutrition_survives_save_and_reload(
        self, recipe, history_path
    ):
        record = self.make_record(recipe)
        manager = JsonDataManager(file_path=history_path)

        assert manager.save_record(record) is True

        reloaded = JsonDataManager(file_path=history_path).load_records()

        assert len(reloaded) == 1
        assert reloaded[0]["nutrition"] == record["nutrition"]
        assert (
            reloaded[0]["nutrition_per_serving"]
            == record["nutrition_per_serving"]
        )
        assert reloaded[0]["nutrition_status"] == "estimated"

    def test_older_record_without_nutrition_can_still_load(self, history_path):
        manager = JsonDataManager(file_path=history_path)

        old_record = {
            "record_id": 1,
            "dish_name": "Older saved recipe",
            "servings": 2,
            "used_ingredients": ["rice"],
            "cooking_time_mins": 10,
        }

        assert manager.save_record(old_record) is True

        reloaded = JsonDataManager(file_path=history_path).load_records()

        assert reloaded == [old_record]
        assert "nutrition" not in reloaded[0]

    def test_displayed_values_match_saved_values(self, recipe):
        record = self.make_record(recipe)
        text = render_recipe(recipe)
        values = record["nutrition_per_serving"]

        assert f"Calories: {values['calories_kcal']:.0f} kcal" in text
        assert f"Protein: {values['protein_g']:.1f} g" in text
        assert f"Carbohydrates: {values['carbohydrates_g']:.1f} g" in text
        assert f"Fat: {values['fat_g']:.1f} g" in text

    def test_display_labels_estimate_and_record_saves_ai_method(self, recipe):
        record = self.make_record(recipe)
        text = render_recipe(recipe)

        assert record["nutrition"]["method"] == "ai_estimate"
        assert "Estimated nutrition per serving:" in text
        assert (
            "Estimated nutrition based on the recipe's ingredient quantities."
            in text
        )
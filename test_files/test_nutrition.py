from copy import deepcopy
import pytest
from ai_layer.recipe_prompt_builder import RecipePromptBuilder
from ai_layer.recipe_schema import RECIPE_RESPONSE_SCHEMA
from ai_layer.nutrition_estimate import NutritionEstimate


@pytest.fixture
def recipe():
    return {
        "servings": 2,
        "nutrition": {
            "basis": "whole_recipe",
            "method": "ai_estimate",
            "calories_kcal": 600,
            "protein_g": 40,
            "carbohydrates_g": 50,
            "fat_g": 26,
        },
    }


class TestNutritionEstimate:
    def test_whole_recipe_estimate_is_validated(self, recipe):
        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate is not None
        assert estimate.to_dict() == recipe["nutrition"]

    def test_per_serving_values_are_calculated(self, recipe):
        estimate = NutritionEstimate.from_recipe(recipe)

        assert estimate.per_serving(2) == {
            "calories_kcal": 300,
            "protein_g": 20,
            "carbohydrates_g": 25,
            "fat_g": 13,
        }

    @pytest.mark.parametrize(
        "value",
        [-1, True, "100", None, float("nan"), float("inf")],
    )
    def test_invalid_nutrient_values_are_unavailable(self, recipe, value):
        recipe["nutrition"]["protein_g"] = value

        assert NutritionEstimate.from_recipe(recipe) is None

    @pytest.mark.parametrize(
        "servings",
        [0, -1, True, "2", None, float("nan"), float("inf")],
    )
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
        [
            ("basis", "per_serving"),
            ("method", "verified"),
        ],
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

class TestNutritionPrompt:
    def test_prompt_requests_whole_recipe_nutrition(self):
        prompt = RecipePromptBuilder().build({})

        assert "WHOLE recipe" in prompt
        assert "all servings combined, not one serving" in prompt

    def test_prompt_requests_all_nutrition_fields(self):
        prompt = RecipePromptBuilder().build({})

        for field in NutritionEstimate.FIELDS:
            assert field in prompt

    def test_prompt_identifies_estimation_method(self):
        prompt = RecipePromptBuilder().build({})

        assert "whole_recipe" in prompt
        assert "ai_estimate" in prompt
        assert "not verified nutritional measurements" in prompt


class TestNutritionSchema:
    def test_recipe_schema_requires_nutrition(self):
        recipe_schema = RECIPE_RESPONSE_SCHEMA["items"]

        assert "nutrition" in recipe_schema["properties"]
        assert "nutrition" in recipe_schema["required"]

    def test_nutrition_schema_requires_numeric_nutrients(self):
        nutrition_schema = (
            RECIPE_RESPONSE_SCHEMA["items"]["properties"]["nutrition"]
        )

        assert nutrition_schema["type"] == "OBJECT"

        for field in NutritionEstimate.FIELDS:
            assert field in nutrition_schema["required"]
            assert nutrition_schema["properties"][field]["type"] == "NUMBER"

    def test_nutrition_schema_requires_whole_recipe_basis(self):
        nutrition_schema = (
            RECIPE_RESPONSE_SCHEMA["items"]["properties"]["nutrition"]
        )

        assert "basis" in nutrition_schema["required"]
        assert nutrition_schema["properties"]["basis"] == {
            "type": "STRING",
            "enum": ["whole_recipe"],
        }

    def test_nutrition_schema_requires_ai_estimate_method(self):
        nutrition_schema = (
            RECIPE_RESPONSE_SCHEMA["items"]["properties"]["nutrition"]
        )

        assert "method" in nutrition_schema["required"]
        assert nutrition_schema["properties"]["method"] == {
            "type": "STRING",
            "enum": ["ai_estimate"],
        }
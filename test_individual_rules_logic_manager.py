import logic_manager as lm
from test_data_logic_manager import TestData


# ==========================================
# INDIVIDUAL RULE TESTS
# ==========================================

class TestIndividualRules:

    def setup_method(self):
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()

    # ==========================================
    # COOKING TIME
    # ==========================================

    def test_cooking_time_passes(self):
        rule = lm.CookingTimeRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should pass because its cooking time "
            "is within the user's maximum cooking time."
        )

    def test_cooking_time_fails(self):
        rule = lm.CookingTimeRule()
        self.ai["cooking_time_minutes"] = 31

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because its cooking time "
            "exceeds the user's 30-minute limit."
        )
        assert "exceeding your 30-minute limit" in result.warning

    # ==========================================
    # DIETARY RESTRICTIONS
    # ==========================================

    def test_dietary_restrictions_pass(self):
        rule = lm.DietaryRestrictionRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should pass because no dietary conflicts were detected."
        )
        assert result.warning is None

    def test_dietary_restrictions_fail(self):
        rule = lm.DietaryRestrictionRule()
        self.ai["dietary_information"]["contains_peanuts"] = True

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because it contains peanuts, "
            "which the user has restricted."
        )
        assert "contains peanuts" in result.warning

    def test_peanut_ingredient_detected(self):
        rule = lm.DietaryRestrictionRule()

        self.ai["dietary_information"]["contains_peanuts"] = False
        self.ai["ingredients"].append({
            "name": "peanut butter",
            "amount": 20,
            "unit": "g"
        })

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because peanut butter is listed "
            "as an ingredient despite the AI dietary information."
        )
        assert "peanut butter" in result.warning.lower()

    def test_general_nut_restriction_detects_almonds(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["nuts"]

        self.ai["ingredients"].append({
            "name": "almonds",
            "amount": 50,
            "unit": "g"
        })

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because almonds are detected "
            "under the user's general nut restriction."
        )
        assert "almonds" in result.warning.lower()

    def test_tree_nut_restriction_detects_cashews(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["tree nuts"]

        self.ai["ingredients"].append({
            "name": "cashews",
            "amount": 30,
            "unit": "g"
        })

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because cashews are detected "
            "under the user's tree nut restriction."
        )
        assert "cashews" in result.warning.lower()

    def test_dairy_restriction_detects_milk(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no dairy"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because milk is detected "
            "under the user's dairy restriction."
        )
        assert "milk" in result.warning.lower()

    def test_egg_restriction_detects_egg(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no eggs"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because eggs are detected "
            "under the user's egg restriction."
        )
        assert "egg" in result.warning.lower()

    def test_soy_restriction_detects_tofu(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no soy"]

        self.ai["ingredients"].append({
            "name": "tofu",
            "amount": 100,
            "unit": "g"
        })

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because tofu is detected "
            "under the user's soy restriction."
        )
        assert "tofu" in result.warning.lower()

    def test_gluten_restriction_detects_bread(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no gluten"]

        self.ai["ingredients"].append({
            "name": "bread",
            "amount": 2,
            "unit": "slices"
        })

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because bread is detected "
            "under the user's gluten restriction."
        )
        assert "bread" in result.warning.lower()

    def test_no_allergen_detected(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no peanuts"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should pass because no restricted peanut "
            "ingredients were detected."
        )

    def test_unverified_restriction_generates_warning(self):
        rule = lm.DietaryRestrictionRule()
        self.user["dietary_restrictions"].append("no seafood")

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should remain valid when the restriction "
            "cannot be verified, while generating a warning."
        )
        assert "Could not verify" in result.warning

    # ==========================================
    # MAIN INGREDIENTS
    # ==========================================

    def test_main_ingredients_pass(self):
        rule = lm.MainIngredientRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should pass because the required main ingredients "
            "are included."
        )

    def test_main_ingredients_fail(self):
        rule = lm.MainIngredientRule()
        self.ai["main_ingredients_used"] = ["egg", "milk"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because not all required main "
            "ingredients are used."
        )

    # ==========================================
    # SERVINGS
    # ==========================================

    def test_servings_pass(self):
        rule = lm.ServingsRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should pass because the servings match "
            "the user's requested amount."
        )

    def test_servings_fail(self):
        rule = lm.ServingsRule()
        self.ai["servings"] = 6

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False, (
            "Recipe should fail because the servings do not match "
            "the user's requested amount."
        )

    # ==========================================
    # MEASUREMENTS
    # ==========================================

    def test_incompatible_units_generate_warning(self):
        rule = lm.MeasurementRule()
        self.ai["ingredients"][1]["unit"] = "ml"

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True, (
            "Recipe should remain valid even when measurement units "
            "cannot be directly compared."
        )
        assert "Cannot compare" in result.warning

    # ==========================================
    # BREAKFAST PREFERENCE
    # ==========================================

    def test_breakfast_preference_matches(self):
        rule = lm.BreakfastPreferenceRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.score == 1, (
            "Breakfast preference score should be 1 "
            "because the recipe matches the user's preference."
        )

    def test_breakfast_preference_does_not_match(self):
        rule = lm.BreakfastPreferenceRule()
        self.ai["is_breakfast"] = False

        result = rule.evaluate(self.user, self.ai)

        assert result.score == 0, (
            "Breakfast preference score should be 0 "
            "because the recipe does not match the user's preference."
        )


# ==========================================
# RUNNING TESTS
# ==========================================

if __name__ == "__main__":
    import pytest
    pytest.main(["-v", "-s", __file__])

import copy
import logic_manager as lm


# ==========================================
# TEST DATA CLASS
# ==========================================

class TestData:

    user = {
        "maximum_cooking_time": 30,
        "dietary_restrictions": ["halal", "no peanuts"],
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
        "dietary_information": {
            "halal_suitable": True,
            "contains_peanuts": False,
        },
        "ingredients": [
            {"name": "egg", "amount": 2, "unit": "pieces"},
            {"name": "spinach", "amount": 100, "unit": "g"},
            {"name": "milk", "amount": 200, "unit": "ml"},
        ],
    }

    @classmethod
    def get_user(cls):
        return copy.deepcopy(cls.user)

    @classmethod
    def get_ai(cls):
        return copy.deepcopy(cls.ai)

    @classmethod
    def variant(cls, base, **changes):
        return {**copy.deepcopy(base), **changes}

    @classmethod
    def ingredient_variant(cls, index, **changes):
        ai = cls.get_ai()
        ai["ingredients"][index].update(changes)
        return ai

# ==========================================
# INDIVIDUAL RULE TESTS
# ==========================================

class TestIndividualRules:

    def setup_method(self):
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()

    # Cooking time

    def test_cooking_time_passes(self):
        rule = lm.CookingTimeRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True

    def test_cooking_time_fails(self):
        rule = lm.CookingTimeRule()
        self.ai["cooking_time_minutes"] = 31

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False
        assert "exceeding your 30-minute limit" in result.warning

    # Dietary restrictions

    def test_dietary_restrictions_pass(self):
        rule = lm.DietaryRestrictionRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.warning is None

    def test_dietary_restrictions_fail(self):
        rule = lm.DietaryRestrictionRule()
        self.ai["dietary_information"]["contains_peanuts"] = True

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False
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

        assert result.passed is False
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

        assert result.passed is False
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

        assert result.passed is False
        assert "cashews" in result.warning.lower()

    def test_dairy_restriction_detects_milk(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no dairy"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False
        assert "milk" in result.warning.lower()

    def test_egg_restriction_detects_egg(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no eggs"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False
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

        assert result.passed is False
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

        assert result.passed is False
        assert "bread" in result.warning.lower()

    def test_no_allergen_detected(self):
        rule = lm.DietaryRestrictionRule()

        self.user["dietary_restrictions"] = ["no peanuts"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True


    def test_unverified_restriction_generates_warning(self):
        rule = lm.DietaryRestrictionRule()
        self.user["dietary_restrictions"].append("no seafood")

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert "Could not verify" in result.warning

    # Main ingredients

    def test_main_ingredients_pass(self):
        rule = lm.MainIngredientRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True

    def test_main_ingredients_fail(self):
        rule = lm.MainIngredientRule()
        self.ai["main_ingredients_used"] = ["egg", "milk"]

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False

    # Servings

    def test_servings_pass(self):
        rule = lm.ServingsRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True

    def test_servings_fail(self):
        rule = lm.ServingsRule()
        self.ai["servings"] = 6

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is False

    # Measurements

    def test_incompatible_units_generate_warning(self):
        rule = lm.MeasurementRule()
        self.ai["ingredients"][1]["unit"] = "ml"

        result = rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert "Cannot compare" in result.warning

    # Breakfast preference

    def test_breakfast_preference_matches(self):
        rule = lm.BreakfastPreferenceRule()
        result = rule.evaluate(self.user, self.ai)

        assert result.score == 1

    def test_breakfast_preference_does_not_match(self):
        rule = lm.BreakfastPreferenceRule()
        self.ai["is_breakfast"] = False

        result = rule.evaluate(self.user, self.ai)

        assert result.score == 0

# ==========================================
# LOGIC MANAGER TESTS
# ==========================================

class TestLogicManager:

    def setup_method(self):
        self.manager = lm.LogicManager()
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()

    def test_valid_recipe_is_accepted(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert result.warning is None

    def test_cooking_time_failure_rejects_recipe(self):
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT

    def test_dietary_failure_rejects_recipe(self):
        self.ai["dietary_information"]["contains_peanuts"] = True

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT

    def test_insufficient_ingredients_rejects_recipe(self):
        self.ai["main_ingredients_used"] = ["egg", "milk"]

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT

    def test_excessive_servings_rejects_recipe(self):
        self.ai["servings"] = 6

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT

    def test_quantity_warning_does_not_reject_recipe(self):
        self.ai["ingredients"][0]["amount"] = 5

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert "but you have only" in result.warning

    def test_breakfast_mismatch_does_not_reject_recipe(self):
        self.ai["is_breakfast"] = False

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert result.score == 0

    def test_multiple_warnings_are_combined(self):
        self.ai["ingredients"][0]["amount"] = 5
        self.ai["servings"] = 1
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT
        assert "exceeding your 30-minute limit" in result.warning
        assert "but you have only" in result.warning
        assert "less than your requested" in result.warning

    def test_missing_ai_field_is_handled(self):
        del self.ai["cooking_time_minutes"]

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT
        assert "CookingTimeRule could not be evaluated" in result.warning

    def test_breakfast_score_is_calculated(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.score == 1

    def test_result_to_dict(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)
        output = result.to_dict()

        assert output["status"] == "ACCEPT"
        assert output["score"] == 1
        assert output["warning"] is None


# ==========================================
# RUNNING TESTS
# ==========================================

if __name__ == "__main__":
    import pytest
    pytest.main(["-v", __file__])

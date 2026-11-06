import logic_manager as lm
from test_data_logic_manager import TestData


# ==========================================
# LOGIC MANAGER TESTS
# ==========================================

class TestLogicManager:

    def setup_method(self):
        self.manager = lm.LogicManager()
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()

    # ==========================================
    # RECIPE ACCEPTANCE AND REJECTION
    # ==========================================

    def test_valid_recipe_is_accepted(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT, (
            "Valid recipe should be accepted because it satisfies "
            "the user's requirements."
        )
        assert result.warning is None, (
            "No warnings should be generated for a valid recipe."
        )

    def test_cooking_time_failure_rejects_recipe(self):
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected because its cooking time "
            "exceeds the user's 30-minute limit."
        )

    def test_dietary_failure_rejects_recipe(self):
        self.ai["dietary_information"]["contains_peanuts"] = True

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected because it contains "
            "peanuts, which the user has restricted."
        )

    def test_insufficient_ingredients_rejects_recipe(self):
        self.ai["main_ingredients_used"] = ["egg", "milk"]

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected because not all required "
            "main ingredients are included."
        )

    def test_excessive_servings_rejects_recipe(self):
        self.ai["servings"] = 6

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected because the number of servings "
            "exceeds the user's requested amount."
        )

    # ==========================================
    # WARNINGS AND NON-REJECTION SCENARIOS
    # ==========================================

    def test_quantity_warning_does_not_reject_recipe(self):
        self.ai["ingredients"][0]["amount"] = 5

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT, (
            "Recipe should remain accepted even when an ingredient "
            "quantity exceeds the available amount."
        )
        assert "but you have only" in result.warning, (
            "A warning should inform the user that the required "
            "ingredient quantity exceeds their available stock."
        )

    def test_breakfast_mismatch_does_not_reject_recipe(self):
        self.ai["is_breakfast"] = False

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT, (
            "Recipe should remain accepted because breakfast preference "
            "is a scoring factor rather than a rejection rule."
        )
        assert result.score == 0, (
            "Recipe should receive a score of 0 because it does not "
            "match the user's breakfast preference."
        )

    def test_multiple_warnings_are_combined(self):
        self.ai["ingredients"][0]["amount"] = 5
        self.ai["servings"] = 1
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected because its cooking time "
            "exceeds the user's maximum limit."
        )
        assert "exceeding your 30-minute limit" in result.warning, (
            "Combined warnings should include the cooking time issue."
        )
        assert "but you have only" in result.warning, (
            "Combined warnings should include the ingredient quantity issue."
        )
        assert "less than your requested" in result.warning, (
            "Combined warnings should include the servings issue."
        )

    # ==========================================
    # ERROR HANDLING
    # ==========================================

    def test_missing_ai_field_is_handled(self):
        del self.ai["cooking_time_minutes"]

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT, (
            "Recipe should be rejected when a required AI response "
            "field is missing and the validation rule cannot be evaluated."
        )
        assert "CookingTimeRule could not be evaluated" in result.warning, (
            "Warning should identify the validation rule "
            "that could not be evaluated."
        )

    # ==========================================
    # RECIPE SCORING
    # ==========================================

    def test_breakfast_score_is_calculated(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.score == 1, (
            "Recipe should receive a score of 1 because it matches "
            "the user's breakfast preference."
        )

    # ==========================================
    # RESULT CONVERSION
    # ==========================================

    def test_result_to_dict(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)
        output = result.to_dict()

        assert output["status"] == "ACCEPT", (
            "Result dictionary should correctly represent "
            "the accepted recipe status."
        )
        assert output["score"] == 1, (
            "Result dictionary should preserve the recipe's score."
        )
        assert output["warning"] is None, (
            "Result dictionary should contain no warning "
            "when the recipe passes all validation rules."
        )


# ==========================================
# RUNNING TESTS
# ==========================================

if __name__ == "__main__":
    import pytest
    pytest.main(["-v", "-s", __file__])

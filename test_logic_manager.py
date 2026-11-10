import logic_manager as lm

from manual_validation_rule_logic_manager import ManualValidationRule
from test_data_logic_manager import TestData


class TestLogicManager:
    """Tests the overall outcome produced by all default rules."""

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
        assert output["manual_validation"] == []
        assert output["validation_state"] == "automated_checks_passed"


class TestManualValidationRule:
    """Tests generic names and special/signature compound names."""

    def setup_method(self):
        self.rule = ManualValidationRule()
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()
        self.user["custom_exclusions"] = ["peanut"]

    def add_ingredient(self, name):
        self.ai["ingredients"].append(
            {
                "name": name,
                "amount": 10,
                "unit": "g",
            }
        )

    def test_vague_ingredient_requires_manual_validation(self):
        self.add_ingredient("special sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert len(result.manual_validation) == 1

        entry = result.manual_validation[0]

        assert entry["ingredient"] == "special sauce"
        assert entry["exclusions_to_check"] == ["peanut"]
        assert entry["status"] == "pending"
        assert entry["reason"]

    def test_vague_seasoning_requires_manual_validation(self):
        self.ai["seasonings"] = ["special seasoning"]

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert [
            entry["ingredient"]
            for entry in result.manual_validation
        ] == ["special seasoning"]

    def test_generic_compound_name_requires_manual_validation(self):
        self.add_ingredient("sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert len(result.manual_validation) == 1
        assert result.manual_validation[0]["ingredient"] == "sauce"

    def test_no_custom_exclusions_means_no_manual_validation(self):
        self.user["custom_exclusions"] = []
        self.add_ingredient("special sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.manual_validation == []

    def test_missing_custom_exclusions_is_supported(self):
        del self.user["custom_exclusions"]
        self.add_ingredient("special sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.manual_validation == []

    def test_specific_compound_name_is_not_flagged_as_vague(self):
        self.add_ingredient("tomato sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.manual_validation == []

    def test_duplicate_names_are_reported_once(self):
        self.add_ingredient("special sauce")
        self.add_ingredient("special sauce")
        self.ai["seasonings"] = ["special sauce"]

        result = self.rule.evaluate(self.user, self.ai)

        assert len(result.manual_validation) == 1
        assert (
            result.manual_validation[0]["ingredient"]
            == "special sauce"
        )

    def test_exclusions_are_normalised_and_deduplicated(self):
        self.user["custom_exclusions"] = [
            " Peanut ",
            "peanut",
            "  ",
        ]
        self.add_ingredient("special sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert len(result.manual_validation) == 1
        assert (
            result.manual_validation[0]["exclusions_to_check"]
            == ["peanut"]
        )

    def test_multiple_vague_names_produce_separate_checks(self):
        self.add_ingredient("special sauce")
        self.ai["seasonings"] = ["signature dressing"]

        result = self.rule.evaluate(self.user, self.ai)

        assert {
            entry["ingredient"]
            for entry in result.manual_validation
        } == {"special sauce", "signature dressing"}

    def test_multiple_exclusions_are_preserved_in_each_check(self):
        self.user["custom_exclusions"] = ["peanut", "sesame"]
        self.add_ingredient("special sauce")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.manual_validation[0]["exclusions_to_check"] == [
            "peanut",
            "sesame",
        ]

    def test_signature_compound_name_requires_manual_validation(self):
        self.add_ingredient("signature spread")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert [
            entry["ingredient"]
            for entry in result.manual_validation
        ] == ["signature spread"]

    def test_descriptor_without_compound_term_is_not_flagged(self):
        self.add_ingredient("special rice")

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.manual_validation == []

    def test_removed_descriptors_do_not_trigger_review(self):
        for name in (
            "house dressing",
            "homemade sauce",
            "secret sauce",
            "mystery sauce",
            "unknown sauce",
            "unspecified sauce",
            "proprietary sauce",
        ):
            self.add_ingredient(name)

        result = self.rule.evaluate(self.user, self.ai)

        assert result.passed is True
        assert result.manual_validation == []


class TestManualValidationLogicManager:
    """Tests manual review alongside overall acceptance and rejection."""

    def setup_method(self):
        self.manager = lm.LogicManager()
        self.user = TestData.get_user()
        self.ai = TestData.get_ai()
        self.user["custom_exclusions"] = ["peanut"]

    def add_ingredient(self, name):
        self.ai["ingredients"].append(
            {
                "name": name,
                "amount": 10,
                "unit": "g",
            }
        )

    def test_vague_recipe_is_accepted_but_remains_pending(self):
        self.add_ingredient("special sauce")

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert result.validation_state == "pending_manual_validation"
        assert len(result.manual_validation) == 1
        assert "manual validation required" in result.reason

    def test_clear_recipe_passes_automated_checks(self):
        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert result.manual_validation == []
        assert result.validation_state == "automated_checks_passed"

    def test_known_conflict_is_rejected_despite_pending_checks(self):
        self.add_ingredient("special sauce")
        self.add_ingredient("peanut butter")

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT
        assert result.validation_state == "rejected"
        assert result.manual_validation
        assert "peanut butter" in result.warning.lower()

    def test_time_failure_is_not_overridden_by_manual_review(self):
        self.add_ingredient("special sauce")
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT
        assert result.validation_state == "rejected"
        assert result.manual_validation
        assert "exceeding your 30-minute limit" in result.warning

    def test_rejected_recipe_without_pending_checks_has_rejected_state(self):
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.REJECT
        assert result.manual_validation == []
        assert result.validation_state == "rejected"

    def test_dictionary_preserves_pending_manual_validation(self):
        self.add_ingredient("special sauce")

        result = self.manager.evaluate_recipe(self.user, self.ai)
        output = result.to_dict()

        assert output["status"] == "ACCEPT"
        assert output["validation_state"] == "pending_manual_validation"
        assert output["manual_validation"] == result.manual_validation
        assert output["manual_validation"][0]["status"] == "pending"

    def test_dictionary_preserves_rejected_state(self):
        self.add_ingredient("special sauce")
        self.ai["cooking_time_minutes"] = 31

        result = self.manager.evaluate_recipe(self.user, self.ai)
        output = result.to_dict()

        assert output["status"] == "REJECT"
        assert output["validation_state"] == "rejected"
        assert output["manual_validation"] == result.manual_validation

    def test_manual_validation_does_not_change_breakfast_score(self):
        self.add_ingredient("special sauce")

        result = self.manager.evaluate_recipe(self.user, self.ai)

        assert result.status == lm.Status.ACCEPT
        assert result.validation_state == "pending_manual_validation"
        assert result.score == 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main(["-v", __file__]))

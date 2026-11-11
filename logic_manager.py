from logic_layer.recipe_rule_logic_manager import RecipeRule
from logic_layer.rule_result_logic_manager import RuleResult
from logic_layer.evaluation_result_logic_manager import EvaluationResult
from logic_layer.status_logic_manager import Status

from logic_layer.cooking_time_rule_logic_manager import CookingTimeRule
from logic_layer.dietary_restriction_rule_logic_manager import DietaryRestrictionRule
from logic_layer.main_ingredient_rule_logic_manager import MainIngredientRule
from logic_layer.servings_rule_logic_manager import ServingsRule
from logic_layer.measurement_rule_logic_manager import MeasurementRule
from logic_layer.breakfast_preference_rule_logic_manager import BreakfastPreferenceRule
from logic_layer.manual_validation_rule_logic_manager import ManualValidationRule


class LogicManager:

    def __init__(self, rules: list[RecipeRule] | None = None):
        # Composition: the manager owns its rules. Defaults are built here,
        # but callers may supply their own (open for extension).
        self.__rules = (
            list(rules)
            if rules is not None
            else self._default_rules()
        )

    @staticmethod
    def _default_rules() -> list[RecipeRule]:
        return [
            CookingTimeRule(),
            DietaryRestrictionRule(),
            MainIngredientRule(),
            ServingsRule(),
            MeasurementRule(),
            BreakfastPreferenceRule(),
            ManualValidationRule(),
        ]

    def _run_rule(
        self,
        rule: RecipeRule,
        user_preferences: dict,
        ai_response: dict,
    ) -> RuleResult:
        # Enforces the RecipeRule contract: always returns a RuleResult,
        # so malformed AI output cannot crash the application.
        try:
            return rule.evaluate(user_preferences, ai_response)
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            return RuleResult(
                passed=False,
                warning=(
                    f"{rule.name} could not be evaluated "
                    f"({type(error).__name__}: {error})."
                ),
            )

    def evaluate_recipe(
        self,
        user_preferences: dict,
        ai_response: dict,
    ) -> EvaluationResult:
        # Polymorphism: every rule is used through the RecipeRule interface
        results = [
            self._run_rule(rule, user_preferences, ai_response)
            for rule in self.__rules
        ]

        warnings = [r.warning for r in results if r.warning]
        combined_warning = " ".join(warnings) if warnings else None
        total_score = sum(r.score for r in results)

        manual_validation = [
            entry
            for result in results
            for entry in result.manual_validation
        ]

        if any(not r.passed for r in results):
            return EvaluationResult(
                status=Status.REJECT,
                reason="Recipe does not meet all requirements.",
                score=total_score,
                warning=combined_warning,
                manual_validation=manual_validation,
            )

        reason = (
            "No automated hard failure found; manual validation required."
            if manual_validation
            else "Recipe meets all requirements."
        )

        return EvaluationResult(
            status=Status.ACCEPT,
            reason=reason,
            score=total_score,
            warning=combined_warning,
            manual_validation=manual_validation,
        )
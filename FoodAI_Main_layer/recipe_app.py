from ai_manager import AiManager
from data_manager import BaseDataManager, JsonDataManager
from IO_manager import IOManager
from logic_manager import LogicManager, Status

from .recipe_presenter import RecipePresenter
from .recipe_translator import RecipeTranslator


class RecipeApp:
    """Runs one recipe request from the user's input to the saved results.
    """

    def __init__(
        self,
        io_manager: IOManager,
        ai_manager: AiManager,
        logic_manager: LogicManager,
        data_manager: BaseDataManager,
    ) -> None:
        self._io_manager = io_manager
        self._ai_manager = ai_manager
        self._logic_manager = logic_manager
        self._data_manager = data_manager
        self._translator = RecipeTranslator()
        self._presenter = RecipePresenter()

    @classmethod
    def create_default(cls) -> "RecipeApp":
        """The real application: console input, Gemini, JSON file storage."""
        return cls(
            io_manager=IOManager(),
            ai_manager=AiManager.from_environment(),
            logic_manager=LogicManager(),
            data_manager=JsonDataManager(),
        )

    def run(self) -> None:
        # Step 1: collect and confirm the user's request.
        request = self._io_manager.collect_recipe_request()
        restricted = sorted(
            self._io_manager.get_all_restricted_ingredients(request["dietary"])
        )

        # Step 2: ask the AI layer for candidate recipes.
        ai_input = self._translator.to_ai_input(request, restricted)
        recipes = self._ai_manager.generate_recipes(ai_input)

        if not recipes:
            self._presenter.show_message(
                "\nSorry, we couldn't generate any recipes right now. "
                "Please check ai_manager_errors.log or try again shortly."
            )
            return

        # Step 3: keep the recipes the logic manager accepts, best first.
        preferences = self._translator.to_logic_preferences(request, restricted)
        accepted = self._accepted_recipes(recipes, preferences)

        if not accepted:
            self._presenter.show_message("\nNo recipes passed validation.")
            return

        # Breakfast matches rank first without rejecting the other valid recipes.
        accepted.sort(key=lambda item: item[1].score, reverse=True)

        # Step 4: save and show each accepted recipe.
        self._save_and_show(accepted, len(recipes), request, ai_input)

    def _accepted_recipes(self, recipes, preferences):
        accepted = []

        for recipe in recipes:
            if not self._ai_manager.is_valid_recipe(recipe):
                name = (
                    recipe.get("recipe_name", "Unnamed recipe")
                    if isinstance(recipe, dict)
                    else "Unnamed recipe"
                )
                self._presenter.show_message(
                    f"\nSkipping '{name}' because its recipe data is malformed."
                )
                continue

            name = recipe.get("recipe_name", "Unnamed recipe")

            try:
                ai_response = self._translator.to_logic_response(recipe)
            except ValueError as error:
                self._presenter.show_message(
                    f"\nSkipping '{name}' because its ingredient "
                    f"quantities are invalid: {error}"
                )
                continue

            evaluation = self._logic_manager.evaluate_recipe(preferences, ai_response)
            if evaluation.status == Status.ACCEPT:
                accepted.append((recipe, evaluation))

        return accepted

    def _save_and_show(self, accepted, total_count, request, ai_input):
        next_id = len(self._data_manager.load_records()) + 1

        self._presenter.show_summary(len(accepted), total_count)

        pending_count = sum(
            bool(evaluation.manual_validation)
            for _, evaluation in accepted
        )

        if pending_count:
            self._presenter.show_message(
                f"{pending_count} displayed recipe(s) require manual validation; "
                "they are not confirmed suitable for your exclusions."
            )

        for recipe, evaluation in accepted:
            record = self._translator.to_record(
                next_id,
                recipe,
                request,
                ai_input,
            )

            #save validated nutrition without changing the original recipe.
            saved_recipe = dict(recipe)
            saved_recipe["nutrition"] = record["nutrition"]
            record["ai_response"] = saved_recipe
            record["manual_validation"] = evaluation.manual_validation
            record["validation_state"] = evaluation.validation_state

            saved = self._data_manager.save_record(record)

            self._presenter.show_recipe(recipe, evaluation, saved)
            next_id += 1

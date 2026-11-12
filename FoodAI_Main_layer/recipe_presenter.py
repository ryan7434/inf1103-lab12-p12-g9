from ai_layer.nutrition_estimate import NutritionEstimate


class RecipePresenter:
    """Prints recipes to the console. Only knows how to display."""

    def __init__(self, output=print):
        self._output = output

    def show_message(self, message):
        self._output(message)

    def show_summary(self, accepted_count, total_count):
        self._output(
            f"\n{accepted_count} of {total_count} generated recipe(s) passed validation:\n"
        )

    def show_recipe(self, recipe, evaluation, saved):
        write = self._output

        write("=" * 60)
        write(
            f"{recipe.get('recipe_name')} "
            f"({recipe.get('estimated_cooking_time_minutes')} min, "
            f"serves {recipe.get('servings')})"
        )
        write("=" * 60)

        if recipe.get("is_breakfast"):
            write("Breakfast dish")

        if recipe.get("description"):
            write(f"\n{recipe['description']}")

        ingredients = recipe.get("ingredients", [])
        if ingredients:
            write("\nIngredients:")
            for ingredient in ingredients:
                write(
                    f" - {ingredient.get('quantity', '')} "
                    f"{ingredient.get('unit', '')} "
                    f"{ingredient.get('name', '')}".rstrip()
                )

        seasonings = recipe.get("seasonings", [])
        if seasonings:
            write("\nSeasonings:")
            for seasoning in seasonings:
                write(f" - {seasoning}")

        instructions = recipe.get("instructions", [])
        if instructions:
            write("\nInstructions:")
            for step_number, step in enumerate(instructions, start=1):
                write(f" {step_number}. {step}")

        # Display this section only when manual checks are required.
        if evaluation.manual_validation:
            write("\nManual validation:")
            write(
                "PENDING — this recipe is not confirmed suitable for your "
                "exclusions. Check the listed items before using them."
            )

            for item in evaluation.manual_validation:
                exclusions = ", ".join(item["exclusions_to_check"])

                write(
                    f" - {item['ingredient']}: check for {exclusions}. "
                    f"{item['reason']}"
                )

        self._show_nutrition(recipe)

        if evaluation.warning:
            write(f"\nNote: {evaluation.warning}")

        if not saved:
            write(
                "\n(Warning: could not save this recipe to recipes_history.json)"
            )

        write("")

    def _show_nutrition(self, recipe):
        """Display validated nutrition estimates per serving."""
        estimate = NutritionEstimate.from_recipe(recipe)

        values = (
            estimate.per_serving(recipe.get("servings"))
            if estimate is not None
            else None
        )

        if values is None:
            self._output("\nEstimated nutrition: unavailable.")
            return

        self._output("\nEstimated nutrition per serving:")
        self._output(f"Calories: {values['calories_kcal']:.0f} kcal")
        self._output(f"Protein: {values['protein_g']:.1f} g")
        self._output(
            f"Carbohydrates: {values['carbohydrates_g']:.1f} g"
        )
        self._output(f"Fat: {values['fat_g']:.1f} g")
        self._output(
            "Estimated nutrition based on the recipe's ingredient quantities."
        )
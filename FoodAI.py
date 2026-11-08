from datetime import datetime
from fractions import Fraction

from ai_manager import AiManager
from data_manager import BaseDataManager, JsonDataManager
from dictionary import (
    DIETARY_CHOICES,
    HALAL_RESTRICTED_INGREDIENTS,
    IngredientCatalog,
)
from IO_manager import IOManager
from logic_manager import LogicManager, Status


class RecipeTranslator:
    """Converts data between the dict shapes each manager expects (adapter)."""

    def __init__(self, catalog=None):
        self._catalog = catalog if catalog is not None else IngredientCatalog()

    def normalise(self, name):
        """Lowercase, collapse spaces and resolve aliases, so 'Eggs' == 'egg'."""
        return self._catalog.normalise(str(name))

    # io_manager -> ai_manager
    def to_ai_input(self, req, restricted_ingredients):
        # Decimal is not JSON-serialisable, so quantities become strings here.
        ingredients = [
            {
                "name": ingredient["name"],
                "quantity": str(ingredient["quantity"]),
                "unit": ingredient["unit"],
            }
            for ingredient in req["ingredients"]
        ]

        return {
            "ingredients": ingredients,
            "dietary_restrictions": list(restricted_ingredients),
            "cuisine": req["cuisine"],
            "meal_type": "Breakfast" if req["breakfast"] else "Any",
            "taste_preference": ", ".join(req["tastes"]),
            "max_cooking_time": req["max_time"],
            "servings": req["servings"],
        }

    # io_manager -> logic_manager
    def dietary_keys(self, req):
        """The restriction keys that DietaryRestrictionRule understands."""
        keys = []
        dietary = req["dietary"]
        choice = dietary["dietary_choice"]

        if choice is not None and DIETARY_CHOICES[choice]["key"] == "halal":
            keys.append("halal")

        if any("peanut" in self.normalise(item) for item in dietary["custom_exclusions"]):
            keys.append("no peanuts")

        return keys

    def to_logic_preferences(self, req, restricted_ingredients):
        return {
            "maximum_cooking_time": req["max_time"],
            "dietary_restrictions": self.dietary_keys(req),
            "restricted_ingredients": list(restricted_ingredients),
            "breakfast_preferred": req["breakfast"],
            # the rules compare numbers, so Decimal becomes float here
            "available_ingredients": [
                {
                    "name": self.normalise(ingredient["name"]),
                    "amount": float(ingredient["quantity"]),
                    "unit": ingredient["unit"],
                }
                for ingredient in req["ingredients"]
            ],
            "servings": req["servings"],
        }

    # ai_manager -> logic_manager
    def to_logic_response(self, recipe):
        """Raises ValueError if an ingredient quantity cannot be read."""
        ingredients = [
            {
                "name": self.normalise(item.get("name", "")),
                "amount": self._to_float(item.get("quantity")),
                "unit": item.get("unit", ""),
            }
            for item in recipe.get("ingredients", [])
        ]

        return {
            "cooking_time_minutes": recipe.get("estimated_cooking_time_minutes", 0),
            "dietary_information": self._derive_dietary_information(recipe),
            "is_breakfast": recipe["is_breakfast"],
            "main_ingredients_used": [item["name"] for item in ingredients],
            "servings": recipe.get("servings", 0),
            "ingredients": ingredients,
            "seasonings": recipe.get("seasonings", []),
        }

    # accepted recipe -> data_manager
    def to_record(self, record_id, recipe, req, ai_input):
        user_names = {self.normalise(item["name"]) for item in req["ingredients"]}
        recipe_names = [
            self.normalise(item.get("name", ""))
            for item in recipe.get("ingredients", [])
        ]
        used = [name for name in recipe_names if name in user_names]
        missing = [name for name in recipe_names if name not in user_names]

        return {
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "dish_name": recipe.get("recipe_name", ""),
            "matched_ingredients_count": len(used),
            "used_ingredients": used,
            "missing_ingredients": missing,
            "seasonings_suggested": recipe.get("seasonings", []),
            "cooking_time_mins": recipe.get("estimated_cooking_time_minutes", 0),
            "servings": recipe.get("servings", 0),
            "cuisine": ai_input["cuisine"],
            "meal_type": ai_input["meal_type"],
            "taste_preference": ai_input["taste_preference"],
            "dietary_restrictions": ai_input["dietary_restrictions"],
            "ai_insight": recipe.get("description", ""),
            "instructions": recipe.get("instructions", []),
        }

    def _derive_dietary_information(self, recipe):
        """The AI schema does not ask for halal/peanut flags, so work them out."""
        names = [
            self.normalise(item.get("name", ""))
            for item in recipe.get("ingredients", [])
        ] + [self.normalise(seasoning) for seasoning in recipe.get("seasonings", [])]

        halal_violation = any(name in HALAL_RESTRICTED_INGREDIENTS for name in names)
        contains_peanuts = any("peanut" in name for name in names)

        return {
            "halal_suitable": "False" if halal_violation else "True",
            "contains_peanuts": "True" if contains_peanuts else "False",
        }

    @staticmethod
    def _to_float(value):
        # accepts "2", "1.5" or "1/2"; anything else is a ValueError
        try:
            amount = float(Fraction(value))
            if amount > 0 and not isinstance(value, bool):
                return amount
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            pass
        raise ValueError(f"Invalid quantity: {value!r}")


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
                    f"  - {ingredient.get('quantity', '')} "
                    f"{ingredient.get('unit', '')} "
                    f"{ingredient.get('name', '')}".rstrip()
                )

        seasonings = recipe.get("seasonings", [])
        if seasonings:
            write("\nSeasonings:")
            for seasoning in seasonings:
                write(f"  - {seasoning}")

        instructions = recipe.get("instructions", [])
        if instructions:
            write("\nInstructions:")
            for step_number, step in enumerate(instructions, start=1):
                write(f"  {step_number}. {step}")

        if evaluation.warning:
            write(f"\nNote: {evaluation.warning}")
        if not saved:
            write("\n(Warning: could not save this recipe to recipes_history.json)")

        write("")


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
        for recipe, evaluation in accepted:
            record = self._translator.to_record(next_id, recipe, request, ai_input)
            record["ai_response"] = recipe
            saved = self._data_manager.save_record(record)

            self._presenter.show_recipe(recipe, evaluation, saved)
            next_id += 1


if __name__ == "__main__":
    RecipeApp.create_default().run()


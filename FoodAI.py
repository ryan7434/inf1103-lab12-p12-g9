from datetime import datetime
from fractions import Fraction

import IO_manager
from ai_manager import AiManager
from logic_manager import LogicManager, Status
from data_manager import JsonDataManager, BaseDataManager
from dictionary import (
    DIETARY_CHOICES,
    HALAL_RESTRICTED_INGREDIENTS,
    IngredientCatalog,
)


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


def main():
    # Step 1: collect and confirm the user's request.
    request = IO_manager.main()
    restricted = sorted(IO_manager.get_all_restricted_ingredients(request["dietary"]))
    translator = RecipeTranslator()
    presenter = RecipePresenter()
 
    # Step 2: translate it into ai_manager's expected shape, then
    # generate candidate recipes via the AI layer.
    ai_input = translator.to_ai_input(request, restricted)
    ai_manager = AiManager.from_environment()
    recipes = ai_manager.generate_recipes(ai_input)
 
    if not recipes:
        presenter.show_message(
            "\nSorry, we couldn't generate any recipes right now. "
            "Please check ai_manager_errors.log or try again shortly."
        )
        return
 
    # Step 3: validate each candidate recipe against the user's hard
    # requirements (cooking time, dietary/halal safety, ingredient
    # overlap, servings, measurements) via logic_manager.
    user_preference = translator.to_logic_preferences(request, restricted)
    logic = LogicManager()
 
    accepted = []

    for recipe in recipes:
        if not ai_manager.is_valid_recipe(recipe):
            recipe_name = (
                recipe.get("recipe_name", "Unnamed recipe")
                if isinstance(recipe, dict)
                else "Unnamed recipe"
            )
            presenter.show_message(
                f"\nSkipping '{recipe_name}' because its recipe "
                "data is malformed."
            )
            continue

        recipe_name = recipe.get("recipe_name", "Unnamed recipe")

        # Convert the AI recipe into the logic manager's expected format.
        # Skip the recipe if its ingredient quantities cannot be parsed.
        try:
            ai_response = translator.to_logic_response(recipe)
        except ValueError as error:
            presenter.show_message(
                f"\nSkipping '{recipe_name}' because its ingredient "
                f"quantities are invalid: {error}"
            )
            continue

        # Check the recipe against the user's preferences and ingredients.
        evaluation = logic.evaluate_recipe(
            user_preference,
            ai_response,
        )

        if evaluation.status == Status.ACCEPT:
            accepted.append((recipe, evaluation))


    if not accepted:
        presenter.show_message("\nNo recipes passed validation.")
        return

    # Rank breakfast matches first without rejecting other valid recipes.
    accepted.sort(
        key=lambda item: item[1].score,
        reverse=True,
    )
    
    # Step 4: persist each accepted recipe via JsonDataManager object.
    data_mgr = JsonDataManager()
    existing_records = data_mgr.load_records()
    next_id = len(existing_records) + 1

    presenter.show_summary(len(accepted), len(recipes))
    for recipe, evaluation in accepted:
        record = translator.to_record(next_id, recipe, request, ai_input)
        record["ai_response"] = recipe
        saved = data_mgr.save_record(record)

        presenter.show_recipe(recipe, evaluation, saved)
        next_id += 1


if __name__ == "__main__":
    main()


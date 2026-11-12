from Io_layer.console_IO_Manager import ConsoleIO
from Io_layer.dietary_input_IO_Manager import DietaryInput
from Io_layer.ingredient_input_IO_Manager import IngredientInput
from Io_layer.preferences_input_IO_Manager import PreferencesInput
from Io_layer.dictionary import IngredientCatalog


class IOManager:
    """Coordinates recipe request input, confirmation and editing."""

    EDIT_DIETARY = "1"
    EDIT_INGREDIENTS = "2"
    EDIT_BREAKFAST = "3"
    EDIT_CUISINE = "4"
    EDIT_TASTES = "5"
    EDIT_MAX_TIME = "6"
    EDIT_SERVINGS = "7"
    EDIT_RESTART = "8"

    EDIT_OPTIONS = {
        EDIT_DIETARY: "Dietary category / foods to avoid",
        EDIT_INGREDIENTS: "Main ingredients",
        EDIT_BREAKFAST: "Breakfast preference",
        EDIT_CUISINE: "Cuisine preference",
        EDIT_TASTES: "Taste preferences",
        EDIT_MAX_TIME: "Maximum cooking time",
        EDIT_SERVINGS: "Preferred servings",
        EDIT_RESTART: "Restart everything",
    }

    def __init__(self, console=None, ingredient_catalog=None):
        self._console = console if console is not None else ConsoleIO()

        self._ingredient_catalog = (
            ingredient_catalog
            if ingredient_catalog is not None
            else IngredientCatalog()
        )

        self._dietary_input = DietaryInput(
            console=self._console,
            ingredient_catalog=self._ingredient_catalog,
        )

        self._ingredient_input = IngredientInput(
            console=self._console,
            ingredient_catalog=self._ingredient_catalog,
            dietary_input=self._dietary_input,
        )

        self._preferences_input = PreferencesInput(console=self._console)

        prefs = self._preferences_input
        self._simple_edits = {
            self.EDIT_BREAKFAST: ("breakfast", prefs.get_breakfast_preference),
            self.EDIT_CUISINE: ("cuisine", prefs.get_cuisine_preference),
            self.EDIT_TASTES: ("tastes", prefs.get_taste_preferences),
            self.EDIT_MAX_TIME: ("max_time", prefs.get_max_cooking_time),
            self.EDIT_SERVINGS: ("servings", prefs.get_preferred_servings),
        }

    # --------------------
    # Dietary restrictions
    # --------------------

    def get_all_restricted_ingredients(self, dietary_details):
        return self._dietary_input.get_all_restricted_ingredients(
            dietary_details
        )

    # -------------------
    # Summary and editing
    # -------------------

    def _collect_ingredients(self, req):
        #recollect the ingredients for the dietary details currently in req
        get_ingredients = self._ingredient_input.get_user_ingredients
        req["ingredients"] = get_ingredients(req["dietary"])

    def display_recipe_request_summary(self, req):
        dietary = req["dietary"]
        exclusions = dietary["custom_exclusions"]
        write = self._console.write
        format_quantity = self._ingredient_input.format_quantity

        ingredient_list = ", ".join(
            f"{i['name']} ({format_quantity(i['quantity'])} {i['unit']})"
            for i in req["ingredients"]
        )
        category = self._dietary_input.category_name(dietary["dietary_choice"])
        foods = ", ".join(exclusions) if exclusions else "None"

        write("\nPlease review your recipe request:")
        write(f"Dietary category: {category}")
        write(f"Foods to avoid: {foods}")
        write(f"Main ingredients: {ingredient_list}")

        self._preferences_input.print_preferences(req, "Taste preferences")

    def confirm_generate_recommendations(self):
        return self._console.get_yes_no(
            "\nGenerate recipe recommendations? (Y/N): "
        )

    def get_edit_choice(self):
        return self._console.choosing_options(
            "Which section would you like to change?", self.EDIT_OPTIONS
        )

    def edit_recipe_request(self, choice, req):
        """Return False only when the user confirms a full restart."""

        if choice == self.EDIT_DIETARY:
            #dhanging dietary details also changes allowed ingredients
            self._console.write(
                "\nChanging dietary details will reset your food "
                "exclusions and ingredients."
            )
            self._console.write("Kindly re-enter your dietary details again.")

            req["dietary"] = self._dietary_input.get_dietary_details()
            self._collect_ingredients(req)

        elif choice == self.EDIT_INGREDIENTS:
            #keep dietary details and recollect ingredients only
            self._collect_ingredients(req)

        elif choice == self.EDIT_RESTART:
            return not self._console.get_yes_no(
                "\nThis will discard everything you had entered. "
                "Are you sure you wish to restart? (Y/N): "
            )

        else:
            #update the selected preference
            key, ask = self._simple_edits[choice]
            req[key] = ask()

        return True

    # ----------------
    # Request workflow
    # ----------------

    def collect_recipe_request(self):
        while True:
            req = {"dietary": self._dietary_input.get_dietary_details()}
            self._collect_ingredients(req)
            self._preferences_input.collect_recipe_preferences(req)

            while True:
                self.display_recipe_request_summary(req)

                if self.confirm_generate_recommendations():
                    self._console.write("\nProceeding to the API layer...")
                    return req

                choice = self.get_edit_choice()

                if not self.edit_recipe_request(choice, req):
                    self._console.write(
                        "\nKindly restart your recipe request "
                        "from the beginning."
                    )
                    break


# ------------------------
# Compatibility functions
# ------------------------

def main():
    #keep the existing IO_manager.main() entry point available for FoodAI, which expects a main() function in IO_manager.py
    return IOManager().collect_recipe_request()


def get_all_restricted_ingredients(dietary_details):
    #keep the existing restriction lookup available to FoodAI
    return IOManager().get_all_restricted_ingredients(dietary_details)


if __name__ == "__main__":
    main()
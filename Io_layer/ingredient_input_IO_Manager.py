from decimal import Decimal, InvalidOperation


class IngredientInput:
    """Collects, validates and confirms the user's available ingredients."""

    UNIT_OPTIONS = {
        "1": "tbsp",
        "2": "tsp",
        "3": "slice",
        "4": "clove",
        "5": "g",
        "6": "kg",
        "7": "ml",
        "8": "L",
        "9": "pieces",
        "10": "Other (type your own unit)",
    }

    OTHER_UNIT_OPTIONS = "10"

    UNIT_MAXIMUM_VALUES = {
        "tbsp": Decimal("32"),  #up to 2 cups
        "tsp": Decimal("96"),  #up to 32 tbsp/2 cups
        "slice": Decimal("20"),
        "clove": Decimal("30"),
        "g": Decimal("5000"),  #5kg
        "kg": Decimal("5"),
        "ml": Decimal("5000"),  #5L
        "l": Decimal("5"),
        "pieces": Decimal("30"),
    }

    def __init__(self, console, ingredient_catalog, dietary_input):
        self._console = console
        self._ingredient_catalog = ingredient_catalog
        self._dietary_input = dietary_input

    @staticmethod
    def format_quantity(quantity):
        #display quantity without unnecessary trailing zeros or decimal point.
        return format(quantity.normalize(), "f")

    def get_unit_measurement(self):
        #select a unit or enter a custom unit containing letters only.
        while True:
            choice = self._console.choosing_options(
                "Please choose a unit of measurement:",
                self.UNIT_OPTIONS,
                "Enter your selected unit of measurement: ",
            )

            if choice != self.OTHER_UNIT_OPTIONS:
                return self.UNIT_OPTIONS[choice]

            custom_unit = " ".join(
                self._console.read(
                    "Enter your unit of measurement: "
                ).lower().split()
            )

            #accept only letters and spaces.
            if custom_unit.replace(" ", "").isalpha():
                return custom_unit

            self._console.write(
                "Unit of measurement must contain letters only, "
                "for example: cups, pieces"
            )

    def get_quantity(self, unit):
        #quantity must be finite, greater than zero and within the limit.
        maximum = self.UNIT_MAXIMUM_VALUES.get(
            unit.lower(),
            Decimal("100"),
        )

        while True:
            quantity_input = self._console.read(
                "Enter quantity: "
            ).strip()

            if not quantity_input:
                self._console.write(
                    "Quantity cannot be blank. Kindly enter a number."
                )
                continue

            try:
                quantity = Decimal(quantity_input)
            except InvalidOperation:
                self._console.write(
                    "Invalid quantity. Kindly enter a number greater than zero."
                )
                continue

            if not quantity.is_finite() or quantity <= 0:
                self._console.write(
                    "Quantity must be a number greater than zero."
                )
                continue

            if quantity > maximum:
                self._console.write(
                    f"Quantity is too large. "
                    f"Maximum for {unit}: {self.format_quantity(maximum)}."
                )
                continue

            return quantity

    def get_valid_ingredient(
        self,
        entered_available_ingredients,
        restricted_ingredients,
    ):
        #prompt the user to enter an ingredient name.
        while True:
            name = self._ingredient_catalog.normalise(
                self._console.read("Enter ingredient name: ")
            )

            if not name:
                self._console.write(
                    "Ingredient name cannot be blank."
                )

            elif name in entered_available_ingredients:
                #no duplicate ingredients allowed.
                self._console.write(
                    "You have already entered this ingredient."
                )

            elif self._ingredient_catalog.is_staple(name):
                #staple ingredients are assumed available.
                self._console.write(
                    f"'{name}' is a basic staple and assumed available."
                )

            elif name in restricted_ingredients:
                self._console.write(
                    f"'{name}' is not allowed under your dietary "
                    "preference or food exclusions/allergies."
                )

            else:
                return name

    def display_ingredients(self, ingredients):
        #display ingredients with their quantities and units.
        self._console.write("\nIngredients entered:")

        for number, ingredient in enumerate(ingredients, start=1):
            quantity = self.format_quantity(ingredient["quantity"])

            self._console.write(
                f"{number}. {ingredient['name']} - "
                f"{quantity} {ingredient['unit']}"
            )

    def get_user_ingredients(self, dietary_details):
        restricted_ingredients = (
            self._dietary_input.get_all_restricted_ingredients(
                dietary_details
            )
        )

        while True:
            ingredients = []
            entered_names = set()

            self._console.write(
                "\nEnter 3 to 5 ingredients you currently have."
            )
            self._console.write(
                "Basic staples such as salt, oil, flour, and soy sauce "
                "are assumed available."
            )
            self._console.write(
                "Inputting ingredients from your dietary restrictions and "
                "exclusions/allergies will be deemed invalid."
            )

            while len(ingredients) < 5:
                self._console.write(
                    f"\nIngredient {len(ingredients) + 1}"
                )

                name = self.get_valid_ingredient(
                    entered_names,
                    restricted_ingredients,
                )
                unit = self.get_unit_measurement()
                quantity = self.get_quantity(unit)

                ingredients.append({
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                })
                entered_names.add(name)

                self._console.write(
                    f"{self.format_quantity(quantity)} {unit} of {name}"
                )

                if len(ingredients) < 3:
                    self._console.write(
                        f"You must enter {3 - len(ingredients)} "
                        "more ingredient(s)."
                    )

                elif len(ingredients) < 5 and not self._console.get_yes_no(
                    "\nWould you like to add another ingredient? (Y/N): "
                ):
                    break

            self.display_ingredients(ingredients)

            if self._console.get_yes_no(
                "\nAre these ingredients correct? (Y/N): "
            ):
                return ingredients

            self._console.write(
                "\nKindly re-enter your ingredients again."
            )
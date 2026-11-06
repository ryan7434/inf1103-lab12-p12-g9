from dictionary import DIETARY_CHOICES


class DietaryInput:
    """Collects and confirms dietary preferences and food exclusions."""

    PRIMARY_DIETARY_CHOICES = frozenset({"1", "2", "3", "4"})
    NO_RESTRICTIONS_CHOICE = "6"
    CUSTOM_EXCLUSIONS_CHOICE = "5"

    def __init__(self, console, ingredient_catalog):
        self._console = console
        self._ingredient_catalog = ingredient_catalog

    def display_dietary_choices(self):
        #display the dietary menu options to the user
        self._console.write("\nChoose your dietary preference:")

        for choice, details in DIETARY_CHOICES.items():
            self._console.write(
                f"{choice}. {details['display_name']}"
            )

        self._console.write(
            "\nSelect option 5 alone or together with options 1 to 4."
        )
        self._console.write(
            "Do not select option 6 with any other option."
        )
        self._console.write("Examples: 1 | 2, 5 | 5 | 6")

    def validate_dietary_choices(self, choices_input):
        #remove spaces so "2, 5" and "2,5" are handled the same.
        choices = choices_input.replace(" ", "").split(",")

        rules = [
            (
                choices == [""],
                "Invalid input. Please enter a dietary option.",
            ),
            (
                "" in choices,
                "Invalid input. Kindly use commas between choices "
                "for example: 2, 5.",
            ),
            (
                not all(choice in DIETARY_CHOICES for choice in choices),
                "Invalid choice. Kindly enter options from 1 to 6 only.",
            ),
            (
                len(choices) != len(set(choices)),
                "Invalid input. Do not repeat the same option more than once.",
            ),
            (
                self.NO_RESTRICTIONS_CHOICE in choices and len(choices) > 1,
                "Do not select option 6 with any other option.",
            ),
            (
                len(choices) > 2,
                "Invalid input. Select one dietary category and, if needed, "
                "option 5 for other exclusions/allergies.",
            ),
            (
                len(choices) == 2
                and self.CUSTOM_EXCLUSIONS_CHOICE not in choices,
                "Choose only one dietary option unless you are also selecting "
                "option 5.",
            ),
        ]

        for failed, message in rules:
            if failed:
                self._console.write(message)
                return None

        return choices

    def primary_restrictions(self, primary_choice):
        #returns normalised restrictions, or an empty set if no category.
        if primary_choice is None:
            return set()

        return {
            self._ingredient_catalog.normalise(item)
            for item in DIETARY_CHOICES[primary_choice][
                "restricted_ingredients"
            ]
        }

    def get_food_exclusions(self, primary_choice):
        #option 5 alone has no automatic restrictions.
        existing = self.primary_restrictions(primary_choice)

        while True:
            text = self._ingredient_catalog.normalise(
                self._console.read(
                    "\nEnter food exclusions/allergies separated by commas "
                    "or type 'none'. "
                )
            )

            if text == "none":
                return []

            #de-duplicate while preserving the user's order.
            items = list(
                dict.fromkeys(
                    self._ingredient_catalog.normalise(item)
                    for item in text.split(",")
                )
            )
            restricted = [item for item in items if item in existing]

            rules = [
                (
                    not text,
                    "Invalid input. Enter up to five food exclusions/allergies, "
                    "or type 'none'.",
                ),
                (
                    "" in items,
                    "Invalid input. Separate each food with one comma and "
                    "kindly do not leave any item blank.",
                ),
                (
                    bool(restricted),
                    "These food items are already excluded by your selected "
                    f"dietary choices: {', '.join(restricted)}.\n"
                    "Kindly enter other food exclusions/allergies.",
                ),
                (
                    len(items) > 5,
                    "You are allowed to only enter a maximum of five "
                    "food exclusions/allergies.",
                ),
            ]

            error = next(
                (message for failed, message in rules if failed),
                None,
            )

            if error is None:
                return items

            self._console.write(error)

    def category_name(self, choice):
        #returns the selected category's display name.
        return DIETARY_CHOICES[
            choice or self.CUSTOM_EXCLUSIONS_CHOICE
        ]["display_name"]

    def confirm_dietary_details(self, primary_choice, custom_exclusions):
        self._console.write("\nPlease confirm your dietary details:")
        self._console.write(
            f"Dietary category: {self.category_name(primary_choice)}"
        )

        if custom_exclusions:
            self._console.write(
                f"Other exclusions/allergies: {', '.join(custom_exclusions)}"
            )

        return self._console.get_yes_no("Is this correct? (Y/N): ")

    def get_dietary_details(self):
        #collect details until the user confirms them.
        while True:
            self.display_dietary_choices()

            selected_choices = self.validate_dietary_choices(
                self._console.read("\nEnter your choice(s): ").strip()
            )

            if selected_choices is None:
                continue

            primary_choice = next(
                (
                    choice
                    for choice in selected_choices
                    if choice in self.PRIMARY_DIETARY_CHOICES
                    or choice == self.NO_RESTRICTIONS_CHOICE
                ),
                None,
            )

            custom_exclusions = (
                self.get_food_exclusions(primary_choice)
                if self.CUSTOM_EXCLUSIONS_CHOICE in selected_choices
                else []
            )

            if self.confirm_dietary_details(
                primary_choice,
                custom_exclusions,
            ):
                return {
                    "dietary_choice": primary_choice,
                    "selected_choices": selected_choices,
                    "custom_exclusions": custom_exclusions,
                }

            self._console.write(
                "\nPlease enter your dietary details again."
            )

    def get_all_restricted_ingredients(self, dietary_details):
        custom = {
            self._ingredient_catalog.normalise(item)
            for item in dietary_details["custom_exclusions"]
        }

        return custom | self.primary_restrictions(
            dietary_details["dietary_choice"]
        )
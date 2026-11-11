class PreferencesInput:
    """Collects and confirms the user's recipe preferences."""

    CUISINE_OPTIONS = {
        "1": "Chinese",
        "2": "Korean",
        "3": "Japanese",
        "4": "Indian",
        "5": "Western",
        "6": "Any",
    }

    TASTE_OPTIONS = {
        "1": "Sweet",
        "2": "Savoury",
        "3": "Spicy",
        "4": "Sour",
        "5": "No preference",
    }

    def __init__(self, console):
        self._console = console

    # ------------------
    # Recipe preferences
    # ------------------

    @staticmethod
    def parse_choices(text, valid_options):
        #returns a list of unique choices from the input text, or None if invalid.
        choices = text.replace(" ", "").split(",")

        if (
            all(c in valid_options for c in choices)
            and len(set(choices)) == len(choices)
        ):
            return choices

        return None

    def get_breakfast_preference(self):
        return self._console.get_yes_no(
            "\nDo you want a breakfast recipe? (Y/N): "
        )

    def get_cuisine_preference(self):
        #choose between Chinese, Korean, Japanese, Indian, Western or Any cuisine preference.
        return self.CUISINE_OPTIONS[
            self._console.choosing_options(
                "Choose your preferred cuisine:",
                self.CUISINE_OPTIONS,
            )
        ]

    def get_taste_preferences(self):
        #choose up to 2 taste preferences or No preference (option 5) which must be selected alone.
        while True:
            self._console.write("\nChoose your taste preference(s):")

            for number, taste in self.TASTE_OPTIONS.items():
                self._console.write(f"{number}. {taste}")

            self._console.write("\nSelect up to 2 options from 1 to 4.")
            self._console.write("Option 5 must be selected alone.")
            self._console.write("Examples: 1 | 1, 3 | 3, 4 | 5")

            choices = self.parse_choices(
                self._console.read("\nKindly enter your choice(s): "),
                self.TASTE_OPTIONS,
            )

            if choices is None:
                self._console.write(
                    "Invalid input. Enter unique options from 1 to 5."
                )

            elif "5" in choices and len(choices) > 1:
                self._console.write(
                    "Option 5, No preference, must be selected alone."
                )

            elif len(choices) > 2:
                self._console.write(
                    "You can only select a maximum of two taste preferences."
                )

            else:
                return [self.TASTE_OPTIONS[choice] for choice in choices]

    def get_max_cooking_time(self):
        #max cooking time in minutues must be a whole number ranging from 5(inclusive) to 180(inclusive)
        return self._console.get_whole_number_in_range(
            "\nMaximum cooking time in minutes (5-180): ",
            5,
            180,
        )

    def get_preferred_servings(self):
        #preferred number of servings must be a whole number ranging from 1 to 5
        return self._console.get_whole_number_in_range(
            "\nPreferred number of servings (1-5): ",
            1,
            5,
        )

    def print_preferences(self, req, taste_label):
        self._console.write(
            f"Breakfast preferred: {'Yes' if req['breakfast'] else 'No'}"
        )
        self._console.write(f"Cuisine preference: {req['cuisine']}")
        self._console.write(
            f"{taste_label}: {', '.join(req['tastes'])}"
        )
        self._console.write(
            f"Maximum cooking time: {req['max_time']} minutes"
        )
        self._console.write(f"Preferred servings: {req['servings']}")

    def confirm_recipe_preferences(self, req):
        #confirm the following recipe preferences entered by the user: breakfast,cuisine, taste, time and servings.
        self._console.write("\nPlease confirm your recipe preferences:")
        self.print_preferences(req, "Taste preference(s)")

        return self._console.get_yes_no("\nIs this correct? (Y/N): ")

    def collect_recipe_preferences(self, req):
        #collect breakfast, cuisine, taste, time and servings until the user confirms.
        while True:
            req["breakfast"] = self.get_breakfast_preference()
            req["cuisine"] = self.get_cuisine_preference()
            req["tastes"] = self.get_taste_preferences()
            req["max_time"] = self.get_max_cooking_time()
            req["servings"] = self.get_preferred_servings()

            if self.confirm_recipe_preferences(req):
                #stop collecting preferences once user enters yes.
                return

            #if user enters no, prompt them to re-enter their preferences.
            self._console.write(
                "\nKindly re-enter your recipe preferences again."
            )
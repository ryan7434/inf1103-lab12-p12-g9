from decimal import Decimal, InvalidOperation

from dictionary import (
    DIETARY_CHOICES,
    INGREDIENT_ALIASES,
    STAPLE_INGREDIENTS,
)

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
    "tbsp": Decimal("32"), #up to 2 cups
    "tsp": Decimal("96"),  #up to 32 tbsp/2 cups
    "slice": Decimal("20"),
    "clove": Decimal("30"),
    "g": Decimal("5000"),  #5kg
    "kg": Decimal("5"),
    "ml": Decimal("5000"), #5L
    "L": Decimal("5"),
    "pieces": Decimal("30"),
}

PRIMARY_DIETARY_CHOICES = {"1", "2", "3", "4"}
NO_RESTRICTIONS_CHOICE = "6"
CUSTOM_EXCLUSIONS_CHOICE = "5"


def normalise_text(text):
    cleaned_text = " ".join(text.lower().split())  #Convert text to lowercase, remove extra spaces and apply ingredient aliases.
    return INGREDIENT_ALIASES.get(cleaned_text, cleaned_text)


def format_quantity(quantity): #display quantity without unnecessary trailing zeros or decimal point.
    text = format(quantity, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def get_yes_no(prompt):
    while True:
        response = input(prompt).strip().lower()

        if response in {"y", "yes"}:
            return True

        if response in {"n", "no"}:
            return False #returns True for yes and False for no, keeps asking until valid input is received.

        print("Invalid input. Please enter Y or N.")


def choosing_options(title, options, prompt="Enter your choice: "):
    #display a menu of options and return the user's choice.
    while True:
        print(f"\n{title}")

        for key, label in options.items():
            print(f"{key}. {label}")

        choice = input(f"\n{prompt}").strip()

        if choice in options:
            return choice

        print(f"Invalid input. Enter a number from 1 to {len(options)}.")

# ---------------
# dietary details
# ---------------

def display_dietary_choices():
    #display the dietary menu options to the user
    print("\nChoose your dietary preference:")

    for choice, details in DIETARY_CHOICES.items():
        print(f"{choice}. {details['display_name']}")

    print("\nSelect option 5 alone or together with options 1 to 4.")
    print("Do not select option 6 with any other option.")
    print("Examples: 1 | 2, 5 | 5 | 6")


def validate_dietary_choices(choices_input):
    choices = choices_input.replace(" ", "").split(",") #remove spaces so inputs like "2, 5" and "2,5" are handled the same.

    #each tuple contains an invalid condition and its matching error message.
    #the first failed rule stops validation immediately.
    rules = [
        (
            choices == [""],
            "Invalid input. Please enter a dietary option.",
        ),
        (
            "" in choices,
            "Invalid input. Kindly use commas between choices for example: 2, 5.",
        ),
        (
            not all(c in DIETARY_CHOICES for c in choices),
            "Invalid choice. Kindly enter options from 1 to 6 only.",
        ),
        (
            len(choices) != len(set(choices)),
            "Invalid input. Do not repeat the same option more than once.",
        ),
        (
            NO_RESTRICTIONS_CHOICE in choices and len(choices) > 1,
            "Do not select option 6 with any other option.",
        ),
        (
            len(choices) > 2,
            "Invalid input. Select one dietary category and, if needed, "
            "option 5 for other exclusions/allergies.",
        ),
        (
            len(choices) == 2 and CUSTOM_EXCLUSIONS_CHOICE not in choices,
            "Choose only one dietary option unless you are also selecting "
            "option 5.",
        ),
    ]

    #print the first relevant error instead of showing all of the error messages.
    for failed, message in rules:
        if failed:
            print(message)
            return None
    return choices


def get_food_exclusions(primary_choice):
    #option 5 on its own (primary_choice is None) has no automatic restrictions and user can enter up to 5 food exclusions/allergies.
    existing = (
        set() if primary_choice is None
        else {normalise_text(i) for i in DIETARY_CHOICES[primary_choice]["restricted_ingredients"]}
)

    while True:
        text = normalise_text(
            input("\nEnter food exclusions/allergies separated by commas "
                  "or type 'none'. ")
        )
        if text == "none":
            return []

        # dict.fromkeys() de-duplicates while preserving the user's order.
        items = list(dict.fromkeys(normalise_text(i) for i in text.split(",")))
        restricted = [i for i in items if i in existing]

        error = next((message for failed, message in [
            (not text,
             "Invalid input. Enter up to five food exclusions/allergies, "
             "or type 'none'."),

            ("" in items,
             "Invalid input. Separate each food with one comma and "
             "kindly do not leave any item blank."),
            (bool(restricted),
             "These food items are already excluded by your selected "
             f"dietary choices: {', '.join(restricted)}.\n"
             "Kindly enter other food exclusions/allergies."),

            (len(items) > 5,
             "You are allowed to only enter a maximum of five "
             "food exclusions/allergies."),
        ] if failed), None)  #only show the error message whose validation condition failed otherwise return none

        if error is None:
            return items
        print(error)


def category_name(choice):
    #returns the display name of the dietary category based on the choice number
    return DIETARY_CHOICES[choice or CUSTOM_EXCLUSIONS_CHOICE]["display_name"]


def confirm_dietary_details(primary_choice, custom_exclusions):
    #confirm the dietary details entered by the user.
    print("\nPlease confirm your dietary details:")
    print(f"Dietary category: {category_name(primary_choice)}")

    if custom_exclusions:
        print(f"Other exclusions/allergies: {', '.join(custom_exclusions)}")

    return get_yes_no("Is this correct? (Y/N): ")


def get_dietary_details():
    #collect and confirm dietary details from the user, returning a dictionary with the collected input from the user
    while True:
        display_dietary_choices()

        selected_choices = validate_dietary_choices(
            input("\nEnter your choice(s): ").strip()
        )

        if selected_choices is None:
            continue

        primary_choices = [
            choice
            for choice in selected_choices
            if choice in PRIMARY_DIETARY_CHOICES
            or choice == NO_RESTRICTIONS_CHOICE
        ]

        primary_choice = primary_choices[0] if primary_choices else None
        custom_exclusions = []

        if CUSTOM_EXCLUSIONS_CHOICE in selected_choices:
            custom_exclusions = get_food_exclusions(primary_choice)

        if confirm_dietary_details(primary_choice, custom_exclusions):
            return {
                "dietary_choice": primary_choice,
                "selected_choices": selected_choices,
                "custom_exclusions": custom_exclusions,
            }

        print("\nPlease enter your dietary details again.")


def get_all_restricted_ingredients(dietary_details):
    restricted = set(dietary_details["custom_exclusions"])
    dietary_choice = dietary_details["dietary_choice"]

    if dietary_choice is not None:
        restricted.update(
            DIETARY_CHOICES[dietary_choice]["restricted_ingredients"]
        )

    return {normalise_text(item) for item in restricted}

# -----------
# Ingredients
# -----------

NORMALISED_STAPLES = {
    normalise_text(staple)
    for staple in STAPLE_INGREDIENTS
}

def get_unit_measurement():
    #user to select UOM from the given options or enter a custom unit, ensuring it contains letters only.
    while True:
        choice = choosing_options(
            "Please choose a unit of measurement:",
            UNIT_OPTIONS,
            "Enter your selected unit of measurement: ",
        )

        if choice != OTHER_UNIT_OPTIONS:
            return UNIT_OPTIONS[choice]

        custom_unit = " ".join(input("Enter your unit of measurement: ").lower().split())

        if custom_unit.replace(" ", "").isalpha(): #accept only letters and spaces (reject numbers and special characters)
            return custom_unit

        print("Unit of measurement must contain letters only, for example: cups, pieces")


def get_quantity(unit):
    #user to enter a quantity for the given unit, ensuring it is a number > 0 and within the maximum allowed for that unit.
    maximum = UNIT_MAXIMUM_VALUES.get(unit, Decimal("100"))

    while True:
        quantity_input = input("Enter quantity: ").strip()

        if not quantity_input:
            print("Quantity cannot be blank. Kindly enter a number.")
            continue

        try:
            quantity = Decimal(quantity_input)
        except InvalidOperation:
            print("Invalid quantity. Kindly enter a number greater than zero.")
            continue

        if not quantity.is_finite() or quantity <= 0:
            print("Quantity must be a number greater than zero.")
            continue

        if quantity > maximum:
            print(
                f"Quantity is too large. "
                f"Maximum for {unit}: {format_quantity(maximum)}."
            )
            continue

        return quantity


def get_valid_ingredient(entered_available_ingredients, restricted_ingredients):
    #prompt the user to enter an ingredient name
    while True:
        ingredient_name = normalise_text(input("Enter ingredient name: "))

        if not ingredient_name:
            print("Ingredient name cannot be blank.")

        elif ingredient_name in entered_available_ingredients: #no duplicate ingredients allowed
            print("You have already entered this ingredient.") 

        elif ingredient_name in NORMALISED_STAPLES: #not allowed to enter staple ingredients
            print(
                f"'{ingredient_name}' is a basic staple"
            )

        elif ingredient_name in restricted_ingredients: #not allowed to enter ingredients from dietary restrictions or custom exclusions/allergies
            print(
                f"'{ingredient_name}' is not allowed under your dietary "
                "preference or food exclusions/allergies."
            )

        else:
            return ingredient_name


def display_ingredients(ingredients):
    #display the list of ingredients entered with their quantities and units.
    print("\nIngredients entered:")

    for number, ingredient in enumerate(ingredients, start=1):
        quantity = format_quantity(ingredient["quantity"])

        print(
            f"{number}. {ingredient['name']} - "
            f"{quantity} {ingredient['unit']}"
        )


def get_user_ingredients(dietary_details):
    restricted_ingredients = get_all_restricted_ingredients(dietary_details)

    while True:
        ingredients = []
        entered_names = set()

        print("\nEnter 3 to 5 ingredients you currently have.")
        print("Basic staples such as salt, oil, flour, and soy sauce are assumed available.")
        print("Inputting ingredients from your dietary restrictions and exclusions/allergies will be deemed invalid.")

        while len(ingredients) < 5: #accepts ingredients until the user has entered 5 or atleast 3.
            print(f"\nIngredient {len(ingredients) + 1}") #show the user the current ingredient number they are entering

            name = get_valid_ingredient(entered_names, restricted_ingredients)
            unit = get_unit_measurement()
            quantity = get_quantity(unit)

            ingredients.append({"name": name, "quantity": quantity, "unit": unit})
            entered_names.add(name)
            print(f"{format_quantity(quantity)} {unit} of {name}")

            if len(ingredients) < 3: #prompt user to add more ingredients if less than 3 entered
                print(f"You must enter {3 - len(ingredients)} more ingredient(s).")
            elif len(ingredients) < 5 and not get_yes_no(
                "\nWould you like to add another ingredient? (Y/N): "
            ):
                break

        display_ingredients(ingredients)

        if get_yes_no("\nAre these ingredients correct? (Y/N): "):
            return ingredients

        print("\nKindly enter your ingredients again.") #if no, prompt user to re-enter ingredients

if __name__ == "__main__":
    dietary_details = get_dietary_details()
    ingredients = get_user_ingredients(dietary_details)
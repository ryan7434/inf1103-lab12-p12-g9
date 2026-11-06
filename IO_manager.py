from console_IO_Manager import ConsoleIO
from dietary_input_IO_Manager import DietaryInput
from ingredient_input_IO_Manager import IngredientInput

from dictionary import IngredientCatalog


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


_ingredient_catalog = IngredientCatalog()

_console_io = ConsoleIO()

_dietary_input = DietaryInput(
    console=_console_io,
    ingredient_catalog=_ingredient_catalog,
)

_ingredient_input = IngredientInput(
    console=_console_io,
    ingredient_catalog=_ingredient_catalog,
    dietary_input=_dietary_input,
)


# Keep existing function names available during the staged refactor.
get_yes_no = _console_io.get_yes_no
choosing_options = _console_io.choosing_options
get_whole_number_in_range = _console_io.get_whole_number_in_range

normalise_text = _ingredient_catalog.normalise
format_quantity = _ingredient_input.format_quantity


# ---------------
# dietary details
# ---------------

display_dietary_choices = _dietary_input.display_dietary_choices
validate_dietary_choices = _dietary_input.validate_dietary_choices
primary_restrictions = _dietary_input.primary_restrictions
get_food_exclusions = _dietary_input.get_food_exclusions
category_name = _dietary_input.category_name
confirm_dietary_details = _dietary_input.confirm_dietary_details
get_dietary_details = _dietary_input.get_dietary_details
get_all_restricted_ingredients = (
    _dietary_input.get_all_restricted_ingredients
)


# -----------
# Ingredients
# -----------

get_unit_measurement = _ingredient_input.get_unit_measurement
get_quantity = _ingredient_input.get_quantity
get_valid_ingredient = _ingredient_input.get_valid_ingredient
display_ingredients = _ingredient_input.display_ingredients
get_user_ingredients = _ingredient_input.get_user_ingredients


# ------------------
# Recipe preferences
# ------------------

def parse_choices(text, valid_options):
    #returns a list of unique choices from the input text, or None if invalid.
    choices = text.replace(" ", "").split(",")

    if (
        all(choice in valid_options for choice in choices)
        and len(set(choices)) == len(choices)
    ):
        return choices

    return None


def get_breakfast_preference():
    return get_yes_no("\nDo you want a breakfast recipe? (Y/N): ")


def get_cuisine_preference():
    #choose between Chinese, Korean, Japanese, Indian, Western or Any cuisine preference.
    return CUISINE_OPTIONS[
        choosing_options(
            "Choose your preferred cuisine:",
            CUISINE_OPTIONS,
        )
    ]


def get_taste_preferences():
    #choose up to 2 taste preferences or No preference (option 5) which must be selected alone.
    while True:
        print("\nChoose your taste preference(s):")

        for number, taste in TASTE_OPTIONS.items():
            print(f"{number}. {taste}")

        print("\nSelect up to 2 options from 1 to 4.")
        print("Option 5 must be selected alone.")
        print("Examples: 1 | 1, 3 | 3, 4 | 5")

        choices = parse_choices(
            input("\nKindly enter your choice(s): "),
            TASTE_OPTIONS,
        )

        if choices is None:
            print("Invalid input. Enter unique options from 1 to 5.")

        elif "5" in choices and len(choices) > 1:
            print("Option 5, No preference, must be selected alone.")

        elif len(choices) > 2:
            print("You can only select a maximum of two taste preferences.")

        else:
            return [TASTE_OPTIONS[choice] for choice in choices]


def get_max_cooking_time():
    #max cooking time in minutues must be a whole number ranging from 5(inclusive) to 180(inclusive)
    return get_whole_number_in_range(
        "\nMaximum cooking time in minutes (5-180): ",
        5,
        180,
    )


def get_preferred_servings():
    #preferred number of servings must be a whole number ranging from 1 to 5
    return get_whole_number_in_range(
        "\nPreferred number of servings (1-5): ",
        1,
        5,
    )


def print_preferences(req, taste_label):
    #prints preference lines shared by the confirmation and summary.
    print(f"Breakfast preferred: {'Yes' if req['breakfast'] else 'No'}")
    print(f"Cuisine preference: {req['cuisine']}")
    print(f"{taste_label}: {', '.join(req['tastes'])}")
    print(f"Maximum cooking time: {req['max_time']} minutes")
    print(f"Preferred servings: {req['servings']}")


def confirm_recipe_preferences(req):
    #confirm the recipe preferences entered by the user.
    print("\nPlease confirm your recipe preferences:")
    print_preferences(req, "Taste preference(s)")

    return get_yes_no("\nIs this correct? (Y/N): ")


def collect_recipe_preferences(req):
    #collect breakfast, cuisine, taste, time and servings until the user confirms.
    while True:
        req["breakfast"] = get_breakfast_preference()
        req["cuisine"] = get_cuisine_preference()
        req["tastes"] = get_taste_preferences()
        req["max_time"] = get_max_cooking_time()
        req["servings"] = get_preferred_servings()

        if confirm_recipe_preferences(req):
            #stop collecting preferences once user enters yes.
            return

        #if user enters no, prompt them to re-enter their preferences.
        print("\nKindly re-enter your recipe preferences again.")


# -------------------
# Summary and editing
# -------------------

def display_recipe_request_summary(req):
    #display a full summary of whatever the user has entered.
    dietary = req["dietary"]
    exclusions = dietary["custom_exclusions"]

    ingredient_list = ", ".join(
        f"{ingredient['name']} "
        f"({format_quantity(ingredient['quantity'])} {ingredient['unit']})"
        for ingredient in req["ingredients"]
    )

    print("\nPlease review your recipe request:")
    print(f"Dietary category: {category_name(dietary['dietary_choice'])}")
    print(f"Foods to avoid: {', '.join(exclusions) if exclusions else 'None'}")
    print(f"Main ingredients: {ingredient_list}")
    print_preferences(req, "Taste preferences")


def confirm_generate_recommendations():
    return get_yes_no("\nGenerate recipe recommendations? (Y/N): ")


def get_edit_choice():
    #ask which section the user would like to edit.
    return choosing_options(
        "Which section would you like to change?",
        EDIT_OPTIONS,
    )


SIMPLE_EDITS = {
    #only requires a single function call to get the new value.
    EDIT_BREAKFAST: ("breakfast", get_breakfast_preference),
    EDIT_CUISINE: ("cuisine", get_cuisine_preference),
    EDIT_TASTES: ("tastes", get_taste_preferences),
    EDIT_MAX_TIME: ("max_time", get_max_cooking_time),
    EDIT_SERVINGS: ("servings", get_preferred_servings),
}


def edit_recipe_request(choice, req):
    if choice == EDIT_DIETARY:
        #changing dietary details also changes which ingredients are allowed,
        #so the user must re-enter their exclusions and ingredient list.
        print(
            "\nChanging dietary details will reset your food exclusions "
            "and ingredients."
        )
        print("Kindly re-enter your dietary details again.")

        req["dietary"] = get_dietary_details()
        req["ingredients"] = get_user_ingredients(req["dietary"])

    elif choice == EDIT_INGREDIENTS:
        #re-enter ingredients while keeping the current dietary details.
        req["ingredients"] = get_user_ingredients(req["dietary"])

    elif choice == EDIT_RESTART:
        #confirm whether the user wants to restart the entire process.
        return not get_yes_no(
            "\nThis will discard everything you had entered. "
            "Are you sure you wish to restart? (Y/N): "
        )

    else:
        key, ask = SIMPLE_EDITS[choice]
        req[key] = ask()

    return True


def main():
    while True:
        req = {"dietary": get_dietary_details()}
        req["ingredients"] = get_user_ingredients(req["dietary"])

        collect_recipe_preferences(req)

        while True:
            display_recipe_request_summary(req)

            if confirm_generate_recommendations():
                print("\nProceeding to the API layer...")
                return req

            if not edit_recipe_request(get_edit_choice(), req):
                print(
                    "\nKindly restart your recipe request from the beginning."
                )
                break


#if __name__ == "__main__": #only run directly, not when imported.
#    request = main()
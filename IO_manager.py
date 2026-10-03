from dictionary import (
    DIETARY_CHOICES,
    INGREDIENT_ALIASES,
)


PRIMARY_DIETARY_CHOICES = {"1", "2", "3", "4"}
NO_RESTRICTIONS_CHOICE = "6"
CUSTOM_EXCLUSIONS_CHOICE = "5"


def normalise_text(text):
    cleaned_text = " ".join(text.lower().split())  #Convert text to lowercase, remove extra spaces and apply ingredient aliases.
    return INGREDIENT_ALIASES.get(cleaned_text, cleaned_text)


def get_yes_no(prompt):
    while True:
        response = input(prompt).strip().lower()

        if response in {"y", "yes"}:
            return True

        if response in {"n", "no"}:
            return False #returns True for yes and False for no, keeps asking until valid input is received.

        print("Invalid input. Please enter Y or N.")


def category_name(choice):
    #returns the display name of the dietary category based on the choice number
    return DIETARY_CHOICES[choice or CUSTOM_EXCLUSIONS_CHOICE]["display_name"]


## Dietary details ##

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
        else DIETARY_CHOICES[primary_choice]["restricted_ingredients"]
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
    #returns a set of all restricted ingredients based on user's dietary choice and custom exclusions the user gave.
    restricted_ingredients = set(dietary_details["custom_exclusions"])
    dietary_choice = dietary_details["dietary_choice"]

    if dietary_choice is not None:
        restricted_ingredients.update( #if a dietary choice is selected, add the restricted ingredients
            DIETARY_CHOICES[dietary_choice]["restricted_ingredients"]
        )

    return restricted_ingredients

if __name__ == "__main__":
    details = get_dietary_details()
    print("\nResult:", details)
    print("All restricted:", get_all_restricted_ingredients(details))
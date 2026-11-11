"""JSON schema the AI is asked to follow when it returns recipes."""


# Makes it so the output is in this format
# This is sent to Gemini (as "responseSchema") so it must reply with a list of
# recipe objects shaped like the one below. Gemini's schema format uses
# upper-case type names such as ARRAY, OBJECT, STRING, NUMBER and BOOLEAN.
RECIPE_RESPONSE_SCHEMA = {
    "type": "ARRAY",      # the reply is a list of recipes
    "items": {
        "type": "OBJECT",    # each recipe is an object with these fields
        "properties": {
            "recipe_name": {"type": "STRING"},
            # List of ingredients, each with a name, quantity and unit.
            # Quantity is a STRING so values like "1/2" are allowed.
            "ingredients": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "quantity": {"type": "STRING"},
                        "unit": {"type": "STRING"},
                    },
                    "required": ["name", "quantity", "unit"],
                },
            },
            "description": {
                "type": "STRING",
                "description": (
                    # The description tells the AI what to write in this field.
                    "Explain how this recipe fits the requested cuisine and taste preference"
                ),
            },
            "seasonings": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            # Step-by-step cooking instructions, one string per step.
            "instructions": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "estimated_cooking_time_minutes": {"type": "NUMBER"},
            "servings": {"type": "NUMBER"},
            "is_breakfast": {
                "type": "BOOLEAN",
                "description": (
                    "True if this recipe is suitable for breakfast, false otherwise"
                ),
            },
        },
        # The AI must include every one of these fields in each recipe.
        "required": [
            "recipe_name",
            "ingredients",
            "description",
            "seasonings",
            "instructions",
            "estimated_cooking_time_minutes",
            "servings",
            "is_breakfast",
        ],
    },
}

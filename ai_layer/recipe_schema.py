"""JSON schema the AI is asked to follow when it returns recipes."""


# Makes it so the output is in this format
RECIPE_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "recipe_name": {"type": "STRING"},
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
                    "Explain how this recipe fits the requested cuisine and taste preference"
                ),
            },
            "seasonings": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
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

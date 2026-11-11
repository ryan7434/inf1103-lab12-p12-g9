class RecipePromptBuilder:
    """Turns the user's request (a dict from the IO layer) into the prompt text."""

    def build(self, user_input: dict) -> str:
         # Turn the ingredient list into one line of text, e.g. "2 pieces egg, 200 g spinach".
        ingredients_text = self._format_ingredients(user_input.get("ingredients", []))
        # Join restrictions with commas, or say "None" if there are no restrictions.
        restrictions_text = ", ".join(user_input.get("dietary_restrictions", [])) or "None"

        # Fill the user's choices into the prompt. .get(key, default) supplies a
        # fallback value when the user did not provide something.
        prompt = f"""
Generate exactly 5 different recipes using these constraints.

Available ingredients: {ingredients_text}
Dietary restrictions / allergies / Halal requirements: {restrictions_text}
Cuisine preference: {user_input.get('cuisine', 'Any')}
Meal type: {user_input.get('meal_type', 'Any')}
Taste preference: {user_input.get('taste_preference', 'Any')}
Maximum cooking time: {user_input.get('max_cooking_time', 'No limit')} minutes
Servings: {user_input.get('servings', 1)}

Ingredient quantity rules:
- Ingredient quantities must be positive numbers or fractions.
- Keep quantity and unit separate.
- For ingredients listed by the user, use the exact unit supplied
  for that ingredient, including custom units. Do not convert it
  or change its spelling.
- For additional ingredients, use these units:
  g, kg, ml, L, tbsp, tsp, pieces, clove, slice.
- Do not use vague quantities such as "a pinch", "a handful" in structured ingredient quantity fields.

Rules:
- Each recipe should use at least 3 of the listed ingredients where possible.
- Scale ingredient quantities to the requested servings.
- Avoid ingredients conflicting with the dietary restrictions.
- Cooking time must not exceed the stated maximum.
- Try to match the requested cuisine where possible, but allow other cuisines if needed. If the cuisine is any, any cuisine is acceptable.
- Keep descriptions and instructions concise.
- Set is_breakfast to true only if the actual dish is normally suitable for breakfast in the requested cuisine. Do not set it to true merely because the requested meal type is Breakfast.
"""
        return prompt.strip()    # strip() removes the blank lines at the start and end of the prompt.

    # Converts the ingredient dicts into readable text, e.g.
    # [{"name": "egg", "quantity": 2, "unit": "pieces"}] -> "2 pieces egg"
    @staticmethod
    def _format_ingredients(ingredients: list) -> str:
        return ", ".join(
            f"{i.get('quantity', '')} {i.get('unit', '')} {i.get('name', '')}".strip()
            for i in ingredients
        ) or "None specified"

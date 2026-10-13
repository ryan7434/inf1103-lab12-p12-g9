1.	Problem Statement and Target Users
o	What real-world problem does your application aim to solve?
Problem Statement: Food waste from not knowing what to cook with what you have in the fridge.
Description: Households often have leftover or partially used ingredients (vegetables that are starting to wilt, half-used packets, small quantities of proteins or grains) that are still suitable for consumption but are discarded as people are unsure of what dishes they can prepare with the ingredients they have available. This is common amongst students and young adults who might have limited cooking experience. 
Most existing recipe platforms, such as Google and YouTube, are primarily designed for users to search for the specific dish and follow a fixed list of ingredients. Users may therefore need to purchase more ingredients for a specific dish, which can result in more leftover or partially used ingredients that may eventually be discarded. This contributes to household food waste, which is a significant environmental and economic issue.
Therefore, there is a need for a solution that can analyse the ingredients a user already has and generate practical recipe suggestions based on their requirements and preference. Our application aims to address this problem by using AI to generate recipes based on the user’s available ingredients, while applying user-defined dietary restrictions and other requirements to ensure that the suggested recipes are suitable for the user.
o	Who are the intended users of the application?
-	Households in general → anyone managing daily grocery shopping and cooking can end up with leftover or randomly-stocked ingredients, and can benefit from suggestions that reduce food waste and simplify meal decisions.
-	Students and young working adults living independently → often have small, irregular grocery hauls and limited cooking experience, making it hard to improvise meals from odd ingredient combinations.
-	Budget-conscious households → want to reduce grocery spending by fully using what they already bought before buying more.
-	Environmentally-conscious consumers → actively trying to reduce personal food waste but lack a practical tool to act on that intention day-to-day.

2.	User Inputs
o	What information or data will users provide to the system?
-	Available Ingredients (User can input up to 5 Ingredients they have on hand - excluding basic staples/seasonings like salt, oil, and pepper, which are assumed available)
-	Dietary restrictions (Halal/Allergies/Food that user does not consume)
-	Cuisine (E.g. Chinese/Korean/Japanese)
-	Meal Type (E.g. Breakfast/Lunch/Dinner/Snack)
-	Craving/Taste Preference (E.g. Sweet/Savoury/Spicy/Sour)
-	Maximum cooking time available
-	Number of servings needed 


3.	Use of AI
o	How will AI be utilized within the application?
-	The application uses AI in the form of a large language model (LLM) to generate recipes with step-by-step instructions after analysing the user’s inputs. It will prioritize recipes that can make use of all ingredients that the user has listed if not minimally three, therefore helping the user to finish his leftover/partially used food before being thrown away. The AI also must take into account of the user’s dietary restrictions, preferences (Eg: Cuisine, Meal Type and Taste), maximum cooking time and the number of servings needed before the recipes are being generated.

o	What outputs, insights, or recommendations will the AI generate from the
user inputs?
-	Recipe (Eg: Dish name)
-	Ingredient list with quantities (It will be scaled to match the number of servings needed based on the user’s input)
-	A short insight to show the user as to why this recipe meets the user’s dietary restrictions and preferences.
-	Seasonings suggestion (Eg: Salt/Pepper/Garlic powder) to make the dish more flavourful
-	Step-by-step cooking instructions
-	Estimated Cooking time (Will not exceed the user’s stated cooking time)

4.	Business Rules
o	What business rules, validations, or decision-making logic will be applied
to the AI-generated outputs?
Business Rule: The application will apply programmed rules to validate and filter AI-generated recipes before displaying them to the user. Users can enter up to five available ingredients, and the system will prioritise recipes that use more of these ingredients to help reduce food waste. Recipes that contain ingredients conflicting with the user's dietary restrictions, allergies, or Halal requirements will be eliminated. The system will also check whether recipes match the user's selected cuisine, meal type, taste preference, maximum cooking time, and required servings. Only recipes that satisfy the required conditions will be considered for recommendation. The remaining recipes will be ranked according to how closely they match the user's requirements and how effectively they use the user's existing ingredients. The top three most suitable recipes will then be displayed. AI outputs will also be validated to ensure that required information such as ingredients, instructions, cooking time, and servings is present before being shown to the user.
Validation:
1.	Maximum 5 ingredients – Users can enter up to 5 ingredients they already have. (user input)
2.	Dietary restrictions – Recipes containing ingredients the user cannot eat will be removed.
3.	Ingredient usage – Recipes must use at least 3 of the user's existing ingredients to be considered valid; recipes that use too few will be excluded.
4.	Ingredient matching – Recipes that use more of the user's existing ingredients will be prioritised. (additional) 
5.	User preferences – Recipes should match the user's selected: Recipes should match the user's selected cooking time and number of servings.
•	Cuisine (use of AI)
•	Meal type (use of AI)
•	Craving/Taste preference (use of AI)
6.	Recipe ranking – After filtering, the system will rank the recipes based on how well they match the user's requirements.
7.	Top 3 results – The system will display the 3 most suitable recipes to the user.
Simple decision-making flow: User inputs → AI generates recipes → Code filters unsuitable recipes → Code ranks remaining recipes → Top 3 recipes displayed

5.	Team Repository Details
https://github.com/ryan7434/inf1103-project1P12G9

MAXIMUM TWO PAGES

STAPLE_INGREDIENTS = {
    # Common Seasonings
    "salt",
    "sea salt",
    "table salt",
    "pepper",
    "black pepper",
    "white pepper",
    "sugar",
    "msg",

    # Common Cooking Oils
    "oil",
    "cooking oil",
    "vegetable oil",
    "canola oil",
    "sunflower oil",
    "olive oil",
    "extra virgin olive oil",
    "sesame oil",

    # Common sauces and condiments
    "soy sauce",
    "light soy sauce",
    "dark soy sauce",
    "ketchup",
    "mustard",
    "vinegar",
    "white vinegar",
    "rice vinegar",
    "apple cider vinegar",
    "balsamic vinegar",
    "hot sauce",
    "chili sauce",

    # Common dried herbs and spices
    "garlic powder",
    "onion powder",
    "chili powder",
    "chilli powder",
    "chili flakes",
    "chilli flakes",
    "paprika",
    "cumin",
    "turmeric",
    "curry powder",
    "cinnamon",
    "oregano",
    "basil",
    "thyme",
    "bay leaves",

    # Common baking and thickening ingredients
    "flour",
    "all-purpose flour",
    "plain flour",
    "cornstarch",
    "cornflour",
    "baking powder",
    "baking soda",
}


# Meat items
MEAT_ITEMS = {
    "beef",
    "minced beef",
    "ground beef",
    "beef steak",
    "beef mince",
    "beef stock",
    "beef broth",
    "pork",
    "pork belly",
    "minced pork",
    "ground pork",
    "pork chop",
    "pork ribs",
    "pork sausage",
    "pork stock",
    "pork broth",
    "bacon",
    "turkey bacon",
    "ham",
    "prosciutto",
    "salami",
    "pepperoni",
    "chorizo",
    "lamb",
    "lamb chop",
    "mutton",
    "veal",
    "venison",
    "chicken",
    "chicken breast",
    "chicken thigh",
    "chicken wing",
    "chicken drumstick",
    "chicken stock",
    "chicken broth",
    "duck",
    "turkey",
    "turkey breast",
    "quail meat",
    "chinese sausage",
    "smoked duck", 
}

# Fish and seafood items
FISH_AND_SEAFOOD_ITEMS = {
    "fish fillet",
    "salmon",
    "tuna",
    "cod",
    "mackerel",
    "sardine",
    "anchovy",
    "anchovies",
    "tilapia",
    "sea bass",
    "prawn",
    "prawns",
    "shrimp",
    "crab",
    "lobster",
    "squid",
    "octopus",
    "clam",
    "mussel",
    "oyster",
    "scallop",
    "fish sauce",
    "oyster sauce",
    "shrimp paste",
    "belacan",
    "cuttlefish",
    "seafood stock",
}

# Items containing animal products used in cooking.
ANIMAL_DERIVED_ITEMS = {
    "gelatin",
    "gelatine",
    "lard",
    "pork fat",
    "pork skin",
    "pork rind",
    "beef tallow",
    "chicken fat",
    "duck fat",
    "animal stock",
}

# Egg
EGG_ITEMS = {
    "egg",
    "egg white",
    "egg yolk",
    "mayonnaise",
    "mayo",
    "casein",
    "salted egg",
    "quail egg",
    "duck egg",
    "century egg",
}

# Dairy products.
DAIRY_ITEMS = {
    "milk",
    "whole milk",
    "skim milk",
    "fresh milk",
    "milk powder",
    "milk solids",
    "evaporated milk",
    "condensed milk",
    "malted milk",
    "buttermilk",
    "cheese",
    "cheddar",
    "mozzarella",
    "parmesan",
    "cream cheese",
    "ricotta",
    "cottage cheese",
    "feta",
    "brie",
    "butter",
    "ghee",
    "cream",
    "whipping cream",
    "heavy cream",
    "cooking cream",
    "sour cream",
    "yogurt",
    "yoghurt",
    "ice cream",
    "custard",
    "whey",
}

# Other items avoided by vegans.
OTHER_ITEMS = {
    "honey",
    "honeycomb",
    "royal jelly",
}

# Alcohol
ALCOHOL_ITEMS = {
    "wine",
    "red wine",
    "white wine",
    "cooking wine",
    "rice wine",
    "marsala",
    "cider",
    "sake",
    "mirin",
}

# Pork-items kept seperately from Meat_items for halal dietary restrictions.
PORK_ITEMS = {
    "pork",
    "pork belly",
    "minced pork",
    "ground pork",
    "pork chop",
    "pork ribs",
    "pork sausage",
    "pork stock",
    "pork broth",
    "bacon",
    "turkey bacon",
    "ham",
    "prosciutto",
    "salami",
    "pepperoni",
    "chorizo",
    "lard",
    "pork fat",
    "pork skin",
    "pork rind",
}

# Combining the restriction groups
VEGETARIAN_RESTRICTED_INGREDIENTS = (
    MEAT_ITEMS
    | FISH_AND_SEAFOOD_ITEMS
    | ANIMAL_DERIVED_ITEMS
)

VEGAN_RESTRICTED_INGREDIENTS = (
    VEGETARIAN_RESTRICTED_INGREDIENTS
    | EGG_ITEMS
    | DAIRY_ITEMS
    | OTHER_ITEMS
)

LACTOSE_INTOLERANT_RESTRICTED_INGREDIENTS = DAIRY_ITEMS

HALAL_RESTRICTED_INGREDIENTS = (
    PORK_ITEMS
    | ALCOHOL_ITEMS
    | {
        "gelatin",
        "gelatine",
        "animal fat",
    }
)

# Maps each dietary-menu option to its identifier, display text and set of restricted ingredients.
DIETARY_CHOICES = {
    "1": {
        "key": "halal",
        "display_name": "Halal preference",
        # Halal preference: filters known pork ingredients, alcohol, and other non-halal ingredients.
        "restricted_ingredients": HALAL_RESTRICTED_INGREDIENTS,
    },

    "2": {
        "key": "vegetarian",
        "display_name": "Vegetarian (Able to consume eggs and dairy products)",
        # Vegetarian option: eggs and dairy are allowed however meat, fish, seafood and animal derived ingredients are excluded 
        "restricted_ingredients": VEGETARIAN_RESTRICTED_INGREDIENTS,
    },

    "3": {
        "key": "vegan",
        "display_name": "Vegan",
        # Vegan option: all vegetarian-restricted ingredients including eggs, dairy and others are excluded.
        "restricted_ingredients": VEGAN_RESTRICTED_INGREDIENTS,
    },

    "4": {
        "key": "lactose_intolerant",
        "display_name": "Lactose intolerant",
        # Lactose intolerant: excludes all dairy products.
        "restricted_ingredients": LACTOSE_INTOLERANT_RESTRICTED_INGREDIENTS,
    },

    "5": {
        "key": "other_exclusions",
        "display_name": "Other food exclusions/allergies (not listed above)",
        # Will allow the user to enter specific food exclusions/allergies manually.
        "restricted_ingredients": set(),
    },

    "6": {
        "key": "none",
        "display_name": "No dietary restrictions",
        "restricted_ingredients": set(),
    },
}
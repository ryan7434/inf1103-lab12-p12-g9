STAPLE_INGREDIENTS = {
    #common Seasonings
    "salt",
    "sea salt",
    "table salt",
    "pepper",
    "black pepper",
    "white pepper",
    "sugar",
    "msg",

    #common Cooking Oils
    "oil",
    "cooking oil",
    "vegetable oil",
    "canola oil",
    "sunflower oil",
    "olive oil",
    "extra virgin olive oil",
    "sesame oil",

    #common sauces and condiments
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

    #common dried herbs and spices
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

    #common baking and thickening ingredients
    "flour",
    "all-purpose flour",
    "plain flour",
    "cornstarch",
    "cornflour",
    "baking powder",
    "baking soda",
}


#meat items
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

#fish and seafood items
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

#items containing animal products used in cooking.
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

#egg
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

#dairy products.
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

#other items avoided by vegans.
OTHER_ITEMS = {
    "honey",
    "honeycomb",
    "royal jelly",
}

#alcohol
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

#pork-items kept seperately from Meat_items for halal dietary restrictions.
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

#UOM that will appear in Recipe.
MEASUREMENT_UNITS = {
    "g",
    "kg",
    "ml",
    "L",
    "tbsp",
    "tsp",
    "pieces",
    "clove",
    "slice"
}

INGREDIENT_ALIASES = {
    "eggs": "egg",
    "egg whites": "egg white",
    "egg yolks": "egg yolk",
    "salted eggs": "salted egg",
    "quail eggs": "quail egg",
    "duck eggs": "duck egg",
    "century eggs": "century egg",

    #common meat cuts and poultry
    "beef steaks": "beef steak",
    "pork bellies": "pork belly",
    "pork chops": "pork chop",
    "pork rib": "pork ribs",
    "pork sausages": "pork sausage",
    "lamb chops": "lamb chop",
    "chicken breasts": "chicken breast",
    "chicken thighs": "chicken thigh",
    "chicken wings": "chicken wing",
    "chicken drumsticks": "chicken drumstick",
    "turkey breasts": "turkey breast",
    "chinese sausages": "chinese sausage",
    "smoked ducks": "smoked duck",

    #common seafood
    "fish": "fish",
    "fish fillets": "fish fillet",
    "sardines": "sardine",
    "anchovies": "anchovy",
    "prawns": "prawn",
    "shrimps": "shrimp",
    "crabs": "crab",
    "lobsters": "lobster",
    "squids": "squid",
    "clams": "clam",
    "mussels": "mussel",
    "oysters": "oyster",
    "scallops": "scallop",

    #animal-derived ingredients
    "gelatins": "gelatin",
    "gelatines": "gelatine",
    "pork fats": "pork fat",
    "pork skins": "pork skin",
    "pork rinds": "pork rind",
    "chicken fats": "chicken fat",
    "duck fats": "duck fat",

    #vegan-restricted animal products
    "honeycombs": "honeycomb",
    "royal jellies": "royal jelly",

    #frequently typed pantry-item variants
    "bay leaf": "bay leaves",
    "chili flake": "chili flakes",
    "chilli flake": "chilli flakes",
    "all purpose flour": "all-purpose flour",
    "corn starch": "cornstarch",
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

#maps each dietary-menu option to its identifier, display text and set of restricted ingredients.
DIETARY_CHOICES = {
    "1": {
        "key": "halal",
        "display_name": "Halal preference",
        #halal preference: filters known pork ingredients, alcohol, and other non-halal ingredients.
        "restricted_ingredients": HALAL_RESTRICTED_INGREDIENTS,
    },

    "2": {
        "key": "vegetarian",
        "display_name": "Vegetarian (Able to consume eggs and dairy products)",
        #vegetarian option: eggs and dairy are allowed however meat, fish, seafood and animal derived ingredients are excluded 
        "restricted_ingredients": VEGETARIAN_RESTRICTED_INGREDIENTS,
    },

    "3": {
        "key": "vegan",
        "display_name": "Vegan",
        #vegan option: all vegetarian-restricted ingredients including eggs, dairy and others are excluded.
        "restricted_ingredients": VEGAN_RESTRICTED_INGREDIENTS,
    },

    "4": {
        "key": "lactose_intolerant",
        "display_name": "Lactose intolerant",
        #lactose intolerant: excludes all dairy products.
        "restricted_ingredients": LACTOSE_INTOLERANT_RESTRICTED_INGREDIENTS,
    },

    "5": {
        "key": "other_exclusions",
        "display_name": "Other food exclusions/allergies (not listed above)",
        #will allow the user to enter specific food exclusions/allergies manually.
        "restricted_ingredients": set(),
    },

    "6": {
        "key": "none",
        "display_name": "No dietary restrictions",
        "restricted_ingredients": set(),
    },
}

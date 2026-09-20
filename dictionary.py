DIETARY_CHOICES = {
    "1": {
        "key": "halal",
        "display_name": "Halal Preference (no pork etc)",
        "restricted_terms": {
            "pork",
            "pork belly",
            "minced pork",
            "bacon",
            "ham",
            "lard",
            "alcohol",
            "beer",
            "wine",
            "cooking wine",
            "rum",
            "brandy",
            "vodka",
            "whisky"
        }
    },

    "2": {
        "key": "vegetarian",
        "display_name": "Vegetarian (eggs & dairy OK)",
        "restricted_terms": {
            "chicken",
            "chicken breast",
            "chicken thigh",
            "beef",
            "pork",
            "pork belly",
            "minced pork",
            "lamb",
            "mutton",
            "duck",
            "turkey",
            "fish",
            "salmon",
            "tuna",
            "cod",
            "prawn",
            "shrimp",
            "crab",
            "squid",
            "clam",
            "mussel",
            "oyster",
            "seafood"
        }
    },

    "3": {
        "key": "vegan",
        "display_name": "Vegan",
        "restricted_terms": {
            "chicken",
            "chicken breast",
            "chicken thigh",
            "beef",
            "pork",
            "pork belly",
            "minced pork",
            "lamb",
            "mutton",
            "duck",
            "turkey",
            "fish",
            "salmon",
            "tuna",
            "cod",
            "prawn",
            "shrimp",
            "crab",
            "squid",
            "clam",
            "mussel",
            "oyster",
            "seafood",
            "egg",
            "eggs",
            "milk",
            "cheese",
            "butter",
            "cream",
            "yogurt",
            "yoghurt",
            "condensed milk",
            "evaporated milk",
            "honey",
            "gelatin",
            "gelatine"
        }
    },

    "4": {
        "key": "lactose_intolerant",
        "display_name": "Lactose intolerant",
        "restricted_terms": {
            "milk",
            "cheese",
            "butter",
            "cream",
            "yogurt",
            "yoghurt",
            "condensed milk",
            "evaporated milk",
            "milk powder",
            "ice cream"
        }
    },

    "5": {
        "key": "other_exclusions",
        "display_name": "Other food exclusions (not listed above)",
        "restricted_terms": set()
    },

    "6": {
        "key": "none",
        "display_name": "No dietary restrictions",
        "restricted_terms": set()
    }
}
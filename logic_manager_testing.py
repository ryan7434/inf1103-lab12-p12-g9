import copy
import logic_manager as lm


# ==========================================
# TEST DATA CLASS
# ==========================================

class TestData:

    user = {
        "maximum_cooking_time": 30,
        "dietary_restrictions": ["halal", "no peanuts"],
        "breakfast_preferred": True,
        "available_ingredients": [
            {"name": "egg", "amount": 4, "unit": "pieces"},
            {"name": "spinach", "amount": 200, "unit": "g"},
            {"name": "milk", "amount": 500, "unit": "ml"},
        ],
        "servings": 2,
    }

    ai = {
        "cooking_time_minutes": 20,
        "is_breakfast": True,
        "main_ingredients_used": ["egg", "spinach", "milk"],
        "servings": 2,
        "dietary_information": {
            "halal_suitable": True,
            "contains_peanuts": False,
        },
        "ingredients": [
            {"name": "egg", "amount": 2, "unit": "pieces"},
            {"name": "spinach", "amount": 100, "unit": "g"},
            {"name": "milk", "amount": 200, "unit": "ml"},
        ],
    }

    @classmethod
    def get_user(cls):
        return copy.deepcopy(cls.user)

    @classmethod
    def get_ai(cls):
        return copy.deepcopy(cls.ai)

    @classmethod
    def variant(cls, base, **changes):
        return {**copy.deepcopy(base), **changes}

    @classmethod
    def ingredient_variant(cls, index, **changes):
        ai = cls.get_ai()
        ai["ingredients"][index].update(changes)
        return ai


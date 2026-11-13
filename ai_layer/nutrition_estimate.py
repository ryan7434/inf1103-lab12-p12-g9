from dataclasses import asdict, dataclass
from math import isfinite
from typing import ClassVar


def _finite_float(value):
    #retuen value as a finite float, or None if it is not a real number
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    try:
        value = float(value)
    except OverflowError:
        return None

    return value if isfinite(value) else None


@dataclass(frozen=True)
class NutritionEstimate:
    #validated AI estimates for the whole recipe

    calories_kcal: float
    protein_g: float
    carbohydrates_g: float
    fat_g: float

    FIELDS: ClassVar[tuple[str, ...]] = (
        "calories_kcal",
        "protein_g",
        "carbohydrates_g",
        "fat_g",
    )

    def __post_init__(self):
        """Reject invalid nutrition values during direct construction."""
        for field in self.FIELDS:
            value = _finite_float(getattr(self, field))

            if value is None or value < 0:
                raise ValueError(
                    f"{field} must be a finite, non-negative number."
                )

    @classmethod
    def from_recipe(cls, recipe):
        #return a validated estimate, or none when unavail
        nutrition = recipe.get("nutrition") if isinstance(recipe, dict) else None

        if (
            not isinstance(nutrition, dict)
            or nutrition.get("basis") != "whole_recipe"
            or nutrition.get("method") != "ai_estimate"
        ):
            return None

        values = {f: _finite_float(nutrition.get(f)) for f in cls.FIELDS}

        if any(v is None or v < 0 for v in values.values()):
            return None

        return cls(**values)

    def per_serving(self, servings):
        #return per serving values, or none for invalid servings
        servings = _finite_float(servings)

        if servings is None or servings <= 0:
            return None

        values = {f: getattr(self, f) / servings for f in self.FIELDS}

        return values if all(isfinite(v) for v in values.values()) else None

    def to_dict(self):
        return {"basis": "whole_recipe", "method": "ai_estimate", **asdict(self)}
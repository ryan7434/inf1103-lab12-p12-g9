"""
test_ai_manager.py - automated tests for the AI Manager.

No live API is used anywhere: replies come from a stub provider or from a
mocked urllib.request.urlopen, so the suite runs offline and inside Docker.

Run with:
    python -m unittest test_ai_manager -v
"""

import contextlib
import inspect
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

import ai_manager as ai


SAMPLE_REQUEST = {
    "ingredients": [
        {"name": "egg", "quantity": "3", "unit": "pieces"},
        {"name": "spinach", "quantity": "100", "unit": "g"},
        {"name": "cheddar", "quantity": "50", "unit": "g"},
    ],
    "dietary_restrictions": ["pork"],
    "cuisine": "Western",
    "meal_type": "Breakfast",
    "taste_preference": "Savoury",
    "max_cooking_time": 20,
    "servings": 2,
}


def good_recipe(**changes):
    recipe = {
        "recipe_name": "Spinach Omelette",
        "ingredients": [
            {"name": "egg", "quantity": "3", "unit": "pieces"},
            {"name": "spinach", "quantity": "1/2", "unit": "g"},
        ],
        "description": "A savoury Western breakfast.",
        "seasonings": ["salt", "pepper"],
        "instructions": ["Whisk eggs.", "Cook in a pan."],
        "estimated_cooking_time_minutes": 12,
        "servings": 2,
        "is_breakfast": True,
    }
    recipe.update(changes)
    return recipe


class TestAIErrorHierarchy(unittest.TestCase):
    def test_every_error_shares_the_ai_error_base(self):
        for error_class in (
            ai.AIConfigurationError,
            ai.AITransportError,
            ai.AIRateLimitError,
            ai.AIResponseError,
        ):
            with self.subTest(error_class=error_class.__name__):
                self.assertTrue(issubclass(error_class, ai.AIError))

    def test_rate_limit_waits_longer_than_other_errors(self):
        self.assertGreater(
            ai.AIRateLimitError.retry_delay_seconds,
            ai.AITransportError.retry_delay_seconds,
        )

    def test_configuration_error_is_not_retryable(self):
        self.assertFalse(ai.AIConfigurationError.retryable)
        self.assertTrue(ai.AITransportError.retryable)
        self.assertTrue(ai.AIResponseError.retryable)

    def test_rate_limit_can_be_handled_as_a_transport_error(self):
        # Liskov: code written for AITransportError also works for its subclass
        self.assertTrue(issubclass(ai.AIRateLimitError, ai.AITransportError))
        with self.assertRaises(ai.AITransportError):
            raise ai.AIRateLimitError("slow down")


if __name__ == "__main__":
    unittest.main(verbosity=2)

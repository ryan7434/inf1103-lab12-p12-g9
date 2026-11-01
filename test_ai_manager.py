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

class TestErrorLogger(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("sys.stdout", new_callable=io.StringIO)
        self.stdout = patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "errors.log")

    def test_writes_a_timestamped_line_and_echoes_it(self):
        ai.ErrorLogger(log_file=self.path).log("something failed")
        with open(self.path, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("something failed", content)
        self.assertTrue(content.startswith("["))
        self.assertIn("[ai_manager] something failed", self.stdout.getvalue())

    def test_appends_instead_of_overwriting(self):
        logger = ai.ErrorLogger(log_file=self.path)
        logger.log("first")
        logger.log("second")
        with open(self.path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(len(lines), 2)

    def test_never_raises_when_the_log_file_cannot_be_written(self):
        logger = ai.ErrorLogger(log_file=self.tmp.name)  # a directory, not a file
        logger.log("still fine")
        self.assertIn("still fine", self.stdout.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)

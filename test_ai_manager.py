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

def fake_http_response(body):
    """A stand-in for what urlopen returns: a context manager with read()."""
    response = mock.MagicMock()
    payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    response.read.return_value = payload
    response.__enter__.return_value = response
    return response


def gemini_body(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def make_gemini(api_key="SECRET-KEY"):
    return ai.GeminiProvider(api_key=api_key, response_schema={"type": "ARRAY"})


class TestGeminiProvider(unittest.TestCase):
    def test_returns_the_reply_text_with_parts_joined(self):
        body = {"candidates": [{"content": {"parts": [{"text": "[1,"}, {"text": " 2]"}]}}]}
        with mock.patch("urllib.request.urlopen", return_value=fake_http_response(body)):
            self.assertEqual(make_gemini().generate("hi"), "[1, 2]")

    def test_request_asks_for_structured_json_with_the_schema(self):
        with mock.patch(
            "urllib.request.urlopen", return_value=fake_http_response(gemini_body("[]"))
        ) as urlopen:
            make_gemini().generate("my prompt")
        request = urlopen.call_args[0][0]
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(ai.GeminiProvider.DEFAULT_MODEL, request.full_url)
        self.assertEqual(sent["contents"][0]["parts"][0]["text"], "my prompt")
        self.assertEqual(sent["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(sent["generationConfig"]["responseSchema"], {"type": "ARRAY"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 90)

    def test_http_429_becomes_a_rate_limit_error(self):
        error = urllib.error.HTTPError("http://x", 429, "Too Many Requests", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ai.AIRateLimitError):
                make_gemini().generate("hi")

    def test_other_http_errors_become_transport_errors_with_the_body(self):
        error = urllib.error.HTTPError(
            "http://x", 500, "Server Error", {}, io.BytesIO(b'{"error": "boom"}')
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ai.AITransportError) as caught:
                make_gemini().generate("hi")
        self.assertIn("500", str(caught.exception))
        self.assertIn("boom", str(caught.exception))
        self.assertNotIn("SECRET-KEY", str(caught.exception))

    def test_network_failure_becomes_a_transport_error(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("no route to host")
        ):
            with self.assertRaises(ai.AITransportError) as caught:
                make_gemini().generate("hi")
        self.assertIn("no route to host", str(caught.exception))

    def test_timeout_becomes_a_transport_error(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=TimeoutError("The read operation timed out")
        ):
            with self.assertRaises(ai.AITransportError) as caught:
                make_gemini().generate("hi")
        self.assertIn("timed out", str(caught.exception))

    def test_a_non_json_http_body_becomes_a_transport_error(self):
        with mock.patch("urllib.request.urlopen", return_value=fake_http_response(b"not json")):
            with self.assertRaises(ai.AITransportError):
                make_gemini().generate("hi")

    def test_no_candidates_becomes_a_response_error(self):
        with mock.patch("urllib.request.urlopen", return_value=fake_http_response({"candidates": []})):
            with self.assertRaises(ai.AIResponseError):
                make_gemini().generate("hi")

    def test_unexpected_response_structure_becomes_a_response_error(self):
        for body in ({"candidates": ["oops"]}, ["not", "a", "dict"]):
            with self.subTest(body=body):
                with mock.patch("urllib.request.urlopen", return_value=fake_http_response(body)):
                    with self.assertRaises(ai.AIResponseError):
                        make_gemini().generate("hi")

    def test_missing_api_key_fails_fast_without_a_request(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(ai.AIConfigurationError):
                make_gemini(api_key="").generate("hi")
        urlopen.assert_not_called()

    def test_api_key_is_not_exposed_as_a_public_or_protected_attribute(self):
        provider = make_gemini()
        self.assertFalse(hasattr(provider, "api_key"))
        self.assertFalse(hasattr(provider, "_api_key"))
        self.assertNotIn("SECRET-KEY", repr(provider))

    def test_model_is_readable_through_a_property(self):
        self.assertEqual(make_gemini().model, ai.GeminiProvider.DEFAULT_MODEL)

class TestRecipePromptBuilder(unittest.TestCase):
    def test_prompt_contains_every_part_of_the_request(self):
        prompt = ai.RecipePromptBuilder().build(SAMPLE_REQUEST)
        for expected in (
            "3 pieces egg",
            "100 g spinach",
            "pork",
            "Western",
            "Breakfast",
            "Savoury",
            "20 minutes",
            "Servings: 2",
            "exactly 5 different recipes",
            "is_breakfast",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, prompt)

    def test_missing_values_fall_back_to_safe_defaults(self):
        prompt = ai.RecipePromptBuilder().build({})
        self.assertIn("Available ingredients: None specified", prompt)
        self.assertIn("requirements: None", prompt)
        self.assertIn("Cuisine preference: Any", prompt)
        self.assertIn("Maximum cooking time: No limit", prompt)

    def test_prompt_has_no_surrounding_whitespace(self):
        prompt = ai.RecipePromptBuilder().build(SAMPLE_REQUEST)
        self.assertEqual(prompt, prompt.strip())

class TestResponseParser(unittest.TestCase):
    def setUp(self):
        self.parser = ai.ResponseParser()

    def test_parses_a_json_list(self):
        self.assertEqual(self.parser.parse('[{"a": 1}]'), [{"a": 1}])

    def test_wraps_a_single_object_in_a_list(self):
        self.assertEqual(self.parser.parse('{"a": 1}'), [{"a": 1}])

    def test_strips_a_markdown_code_fence(self):
        self.assertEqual(self.parser.parse('```json\n[{"a": 1}]\n```'), [{"a": 1}])

    def test_garbage_raises_a_response_error_with_a_preview(self):
        with self.assertRaises(ai.AIResponseError) as caught:
            self.parser.parse("not json at all {broken")
        self.assertIn("not json at all", str(caught.exception))

    def test_empty_text_raises_a_response_error(self):
        for text in ("", "   ", None):
            with self.subTest(text=text):
                with self.assertRaises(ai.AIResponseError):
                    self.parser.parse(text)

    def test_json_that_is_not_a_list_or_object_raises(self):
        for text in ('"just a string"', "42", "null"):
            with self.subTest(text=text):
                with self.assertRaises(ai.AIResponseError):
                    self.parser.parse(text)


class TestResponseValidatorContract(unittest.TestCase):
    def test_the_abstract_base_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            ai.ResponseValidator()

    def test_recipe_validator_is_a_response_validator(self):
        self.assertIsInstance(ai.RecipeValidator(), ai.ResponseValidator)

    def test_filter_valid_keeps_only_valid_items_in_order(self):
        first, third = good_recipe(recipe_name="A"), good_recipe(recipe_name="C")
        kept = ai.RecipeValidator().filter_valid([first, {"recipe_name": "bad"}, third, "junk"])
        self.assertEqual(kept, [first, third])


class TestRecipeValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ai.RecipeValidator()

    def assertInvalid(self, recipe):
        self.assertFalse(self.validator.is_valid(recipe))

    def test_a_complete_recipe_is_valid(self):
        self.assertTrue(self.validator.is_valid(good_recipe()))

    def test_empty_seasonings_list_is_allowed(self):
        self.assertTrue(self.validator.is_valid(good_recipe(seasonings=[])))

    def test_every_required_field_is_needed(self):
        for field in ai.RecipeValidator.REQUIRED_FIELDS:
            with self.subTest(missing=field):
                recipe = good_recipe()
                del recipe[field]
                self.assertInvalid(recipe)

    def test_wrong_field_types_are_rejected(self):
        for field, value in (
            ("recipe_name", 5),
            ("servings", "two"),
            ("estimated_cooking_time_minutes", "12"),
            ("is_breakfast", "yes"),
            ("ingredients", "eggs"),
            ("instructions", "Cook it."),
        ):
            with self.subTest(field=field):
                self.assertInvalid(good_recipe(**{field: value}))

    def test_a_boolean_is_not_accepted_as_a_number(self):
        self.assertInvalid(good_recipe(servings=True))
        self.assertInvalid(good_recipe(estimated_cooking_time_minutes=False))

    def test_not_a_dict_is_rejected(self):
        for item in ("a string", None, 5, ["list"]):
            with self.subTest(item=item):
                self.assertInvalid(item)

    def test_ingredient_problems_are_rejected(self):
        bad_lists = (
            [],
            ["egg"],
            [{"name": "egg", "quantity": "3"}],
            [{"name": " ", "quantity": "3", "unit": "pieces"}],
            [{"name": "egg", "quantity": 3, "unit": "pieces"}],
            [{"name": "egg", "quantity": "3", "unit": ""}],
        )
        for ingredients in bad_lists:
            with self.subTest(ingredients=ingredients):
                self.assertInvalid(good_recipe(ingredients=ingredients))

    def test_instruction_and_seasoning_problems_are_rejected(self):
        self.assertInvalid(good_recipe(instructions=[]))
        self.assertInvalid(good_recipe(instructions=["Whisk.", "  "]))
        self.assertInvalid(good_recipe(instructions=["Whisk.", 5]))
        self.assertInvalid(good_recipe(seasonings=["salt", ""]))
        self.assertInvalid(good_recipe(seasonings=[None]))

if __name__ == "__main__":
    unittest.main(verbosity=2)

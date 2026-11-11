"""AI layer: prompt building, provider calls, parsing and validation.
    makes folder a real package meaning a folder of modules you can import from
"""

from .ai_provider import AIProvider
from .gemini_provider import GeminiProvider
from .error_logger import ErrorLogger
from .ai_error import AIError
from .ai_configuration_error import AIConfigurationError
from .ai_transport_error import AITransportError
from .ai_rate_limit_error import AIRateLimitError
from .ai_response_error import AIResponseError
from .recipe_validator import RecipeValidator
from .response_validator import ResponseValidator
from .response_parser import ResponseParser
from .recipe_prompt_builder import RecipePromptBuilder

__all__ = [
    "AIProvider", "GeminiProvider", "ErrorLogger",
    "AIError", "AIConfigurationError", "AITransportError",
    "AIRateLimitError", "AIResponseError",
    "RecipeValidator", "ResponseValidator", "ResponseParser",
    "RecipePromptBuilder",
]

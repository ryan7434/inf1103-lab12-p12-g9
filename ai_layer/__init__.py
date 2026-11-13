"""AI layer: prompt building, provider calls, parsing and validation.
    makes folder a real package meaning a folder of modules you can import from
"""

# Importing the classes here lets other files write `from ai_layer import AIError`
# instead of naming the individual module file each time.
from .ai_provider import AIProvider
from .gemini_provider import GeminiProvider
from .error_logger import ErrorLogger
from .ai_error import AIError
from .ai_configuration_error import AIConfigurationError
from .ai_transport_error import AITransportError
from .ai_rate_limit_error import AIRateLimitError
from .ai_overloaded_error import AIOverloadedError
from .ai_response_error import AIResponseError
from .fallback_provider import FallbackProvider
from .recipe_validator import RecipeValidator
from .response_validator import ResponseValidator
from .response_parser import ResponseParser
from .recipe_prompt_builder import RecipePromptBuilder

# __all__ lists the names that `from ai_layer import *` will expose.
__all__ = [
    "AIProvider", "GeminiProvider", "ErrorLogger",
    "AIError", "AIConfigurationError", "AITransportError",
    "AIRateLimitError", "AIOverloadedError", "AIResponseError",
    "FallbackProvider",
    "RecipeValidator", "ResponseValidator", "ResponseParser",
    "RecipePromptBuilder",
]
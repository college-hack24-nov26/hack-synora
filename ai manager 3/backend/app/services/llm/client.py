import abc
import json
import logging
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

logger = logging.getLogger("finance_app.llm")


class LLMError(Exception):
    """Base exception for LLM provider failures."""
    pass


class LLMClient(abc.ABC):
    """
    Provider-agnostic abstract client for structured JSON completions.
    All adapters must parse and return a Python dictionary matching the requested schema.
    """

    @abc.abstractmethod
    async def complete_json(
        self,
        system: str,
        user: str,
        schema: Optional[Type[BaseModel]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        model_tier: str = "fast",  # "fast" for categorization, "smart" for insights
    ) -> Dict[str, Any]:
        """
        Executes a completion request and parses the result strictly as JSON.
        """
        pass


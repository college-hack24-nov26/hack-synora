import datetime
import logging
from typing import Optional, Dict
from app.core.config import settings
from app.core.errors import TooManyRequestsException
from app.services.llm.client import LLMClient
from app.services.llm.mock_adapter import MockLLMAdapter
from app.services.llm.anthropic_adapter import AnthropicAdapter
from app.services.llm.gemini_adapter import GeminiAdapter
from app.services.llm.openai_adapter import OpenAIAdapter

logger = logging.getLogger("finance_app.llm.factory")

# In-memory daily counter fallback if Redis is offline
_DAILY_USER_AI_CALLS: Dict[str, int] = {}
_LAST_RESET_DATE = datetime.date.today()


def _get_daily_key(user_id: str) -> str:
    today_str = datetime.date.today().isoformat()
    return f"ai_usage:{user_id}:{today_str}"


async def check_user_daily_ai_limit(user_id: str) -> None:
    """
    Checks and increments daily AI model usage counter per user.
    Raises TooManyRequestsException if user exceeds daily quota.
    """
    global _LAST_RESET_DATE, _DAILY_USER_AI_CALLS
    today = datetime.date.today()
    if today != _LAST_RESET_DATE:
        _DAILY_USER_AI_CALLS.clear()
        _LAST_RESET_DATE = today

    daily_key = _get_daily_key(user_id)
    current_count = _DAILY_USER_AI_CALLS.get(daily_key, 0)
    if current_count >= settings.LLM_DAILY_LIMIT_PER_USER:
        raise TooManyRequestsException(
            f"Daily AI processing limit of {settings.LLM_DAILY_LIMIT_PER_USER} calls reached. Resets at midnight UTC."
        )
    _DAILY_USER_AI_CALLS[daily_key] = current_count + 1


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Factory function returning the active LLM client adapter.
    """
    active = (provider or settings.LLM_PROVIDER).lower().strip()

    if active == "anthropic":
        return AnthropicAdapter()
    elif active == "gemini":
        return GeminiAdapter()
    elif active == "openai":
        return OpenAIAdapter()
    elif active == "mock":
        return MockLLMAdapter()
    else:
        logger.warning("Unrecognized LLM_PROVIDER '%s'. Defaulting to MockLLMAdapter.", active)
        return MockLLMAdapter()


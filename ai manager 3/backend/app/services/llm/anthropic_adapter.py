import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
import anthropic
from app.core.config import settings
from app.services.llm.client import LLMClient, LLMError

logger = logging.getLogger("finance_app.llm.anthropic")

# Model aliases mapping friendly names to official Anthropic model identifiers
ANTHROPIC_MODEL_MAP = {
    "claude-haiku-5-5": "claude-3-5-haiku-20241022",
    "claude-sonnet-5-5": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
}


class AnthropicAdapter(LLMClient):
    """
    Adapter for Anthropic Claude models (Claude 3.5 Haiku & Sonnet).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning("Anthropic API key is not configured.")

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: Optional[Type[BaseModel]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        model_tier: str = "fast",
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured in environment.")

        # Resolve model name
        target_model = settings.LLM_MODEL_FAST if model_tier == "fast" else settings.LLM_MODEL_SMART
        model_id = ANTHROPIC_MODEL_MAP.get(target_model, target_model)

        # Enforce JSON formatting constraint in system prompt
        json_system = (
            f"{system}\n\nCRITICAL INSTRUCTION: Output ONLY a valid JSON object. "
            f"Do not include markdown codeblocks (```json), commentary, or extra text."
        )

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=15.0)
                response = await client.messages.create(
                    model=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=json_system,
                    messages=[{"role": "user", "content": user}],
                )

                # Log token usage safely without exposing prompt content
                in_tokens = response.usage.input_tokens
                out_tokens = response.usage.output_tokens
                logger.info(
                    "Anthropic call succeeded: model=%s in_tokens=%d out_tokens=%d",
                    model_id,
                    in_tokens,
                    out_tokens,
                )

                raw_text = response.content[0].text.strip()
                # Clean up any potential markdown wraps
                clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                clean_text = re.sub(r"\s*```$", "", clean_text).strip()

                parsed = json.loads(clean_text)
                if schema:
                    # Validate against pydantic schema if provided
                    validated = schema.model_validate(parsed)
                    return validated.model_dump()
                return parsed

            except json.JSONDecodeError as jde:
                logger.warning("Anthropic returned non-JSON output on attempt %d: %s", attempt + 1, jde)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"Failed to parse Anthropic JSON output: {jde}") from jde

            except Exception as exc:
                logger.warning("Anthropic API error on attempt %d: %s", attempt + 1, exc)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"Anthropic API failed after {max_retries + 1} attempts: {exc}") from exc


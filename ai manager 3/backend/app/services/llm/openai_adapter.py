import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.services.llm.client import LLMClient, LLMError

logger = logging.getLogger("finance_app.llm.openai")


class OpenAIAdapter(LLMClient):
    """
    Adapter for OpenAI models (GPT-4o Mini & GPT-4o) using native json_object mode.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

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
            raise LLMError("OPENAI_API_KEY is not configured in environment.")

        model = "gpt-4o-mini" if model_tier == "fast" else "gpt-4o"
        url = "https://api.openai.com/v1/chat/completions"

        # In OpenAI json_object mode, the prompt must explicitly mention JSON
        system_prompt = f"{system}\n\nRespond with valid JSON."

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                usage = data.get("usage", {})
                logger.info(
                    "OpenAI call succeeded: model=%s in_tokens=%d out_tokens=%d",
                    model,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                )

                raw_text = data["choices"][0]["message"]["content"].strip()
                clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                clean_text = re.sub(r"\s*```$", "", clean_text).strip()

                parsed = json.loads(clean_text)
                if schema:
                    validated = schema.model_validate(parsed)
                    return validated.model_dump()
                return parsed

            except json.JSONDecodeError as jde:
                logger.warning("OpenAI JSON parse failed on attempt %d: %s", attempt + 1, jde)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"Failed to parse OpenAI JSON: {jde}") from jde

            except Exception as exc:
                logger.warning("OpenAI API error on attempt %d: %s", attempt + 1, exc)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"OpenAI API failed after {max_retries + 1} attempts: {exc}") from exc


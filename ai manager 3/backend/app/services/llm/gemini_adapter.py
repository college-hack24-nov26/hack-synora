import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.services.llm.client import LLMClient, LLMError

logger = logging.getLogger("finance_app.llm.gemini")


class GeminiAdapter(LLMClient):
    """
    Adapter for Google Gemini models via official v1beta REST API.
    Uses responseMimeType="application/json" for guaranteed valid JSON.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

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
            raise LLMError("GEMINI_API_KEY is not configured in environment.")

        model = "gemini-1.5-flash" if model_tier == "fast" else "gemini-1.5-pro"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                usage = data.get("usageMetadata", {})
                logger.info(
                    "Gemini call succeeded: model=%s in_tokens=%d out_tokens=%d",
                    model,
                    usage.get("promptTokenCount", 0),
                    usage.get("candidatesTokenCount", 0),
                )

                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMError("Gemini returned empty candidate list.")

                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                clean_text = re.sub(r"\s*```$", "", clean_text).strip()

                parsed = json.loads(clean_text)
                if schema:
                    validated = schema.model_validate(parsed)
                    return validated.model_dump()
                return parsed

            except json.JSONDecodeError as jde:
                logger.warning("Gemini JSON parse failed on attempt %d: %s", attempt + 1, jde)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"Failed to parse Gemini JSON: {jde}") from jde

            except Exception as exc:
                logger.warning("Gemini API error on attempt %d: %s", attempt + 1, exc)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    raise LLMError(f"Gemini API failed after {max_retries + 1} attempts: {exc}") from exc


import json
import logging
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from app.services.llm.client import LLMClient, LLMError

logger = logging.getLogger("finance_app.llm.mock")


class MockLLMAdapter(LLMClient):
    """
    Deterministic mock LLM adapter for reliable offline testing, developer sanity checks,
    and CI environments.
    """

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: Optional[Type[BaseModel]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        model_tier: str = "fast",
    ) -> Dict[str, Any]:
        # Track minimal metadata: log token counts, NEVER prompt content
        simulated_prompt_tokens = len(system.split()) + len(user.split())
        simulated_completion_tokens = 50
        logger.info(
            "Mock LLM completion: tier=%s prompt_tokens=%d completion_tokens=%d",
            model_tier,
            simulated_prompt_tokens,
            simulated_completion_tokens,
        )

        # Failure trigger for testing error handling and graceful fallbacks
        if "SIMULATE_LLM_FAILURE" in user or "TRIGGER_ERROR" in user:
            raise LLMError("Simulated LLM upstream gateway timeout (HTTP 504)")

        user_lower = user.lower()

        # 1. Transaction Categorization Flow
        if "categorize" in user_lower or "transactions" in user_lower or "merchant" in user_lower:
            try:
                # Try to extract embedded transaction array from prompt
                json_match = re.search(r"(\[\s*\{.*?\}\s*\])", user, re.DOTALL)
                items = json.loads(json_match.group(1)) if json_match else []
            except Exception:
                items = []

            results = []
            if not items:
                # Fallback if raw text prompt
                items = [{"id": "item_1", "merchant": user_lower, "description": user_lower}]

            for item in items:
                text = f"{item.get('merchant', '')} {item.get('description', '')}".lower()
                txn_id = item.get("id") or item.get("transaction_id", "default")

                if any(w in text for w in ["swiggy", "zomato", "restaurant", "starbucks", "cafe", "dining", "dominos", "kfc"]):
                    cat = "Food & Dining"
                    conf = 0.95
                elif any(w in text for w in ["blinkit", "zepto", "instamart", "bigbasket", "dmart", "groceries", "supermarket"]):
                    cat = "Groceries"
                    conf = 0.94
                elif any(w in text for w in ["uber", "ola", "rapido", "metro", "petrol", "fuel", "flight", "indigo", "travel"]):
                    cat = "Travel"
                    conf = 0.92
                elif any(w in text for w in ["cult.fit", "curefit", "gym", "fitness", "badminton", "crossfit"]):
                    cat = "Health"
                    conf = 0.88
                elif any(w in text for w in ["aws", "github", "digitalocean", "cloudflare", "hosting", "software", "chatgpt"]):
                    cat = "Bills & Utilities"
                    conf = 0.91
                elif any(w in text for w in ["udemy", "coursera", "school", "college", "tuition", "course", "education"]):
                    cat = "Education"
                    conf = 0.89
                elif any(w in text for w in ["netflix", "spotify", "prime", "movie", "cinema", "entertainment"]):
                    cat = "Subscriptions"
                    conf = 0.96
                elif "low_confidence" in text or "ambiguous" in text or "unknown_corp" in text or "mystery" in text:
                    # Deliberate low-confidence trigger (< 0.6 threshold)
                    cat = "Uncategorized"
                    conf = 0.45
                else:
                    # Generic fallback
                    cat = "Uncategorized"
                    conf = 0.50

                results.append({
                    "id": txn_id,
                    "category": cat,
                    "confidence": conf,
                })

            return {"results": results}

        # 2. Savings Suggestions & Insights Flow
        if "insight" in user_lower or "saving" in user_lower or "suggestion" in user_lower:
            return {
                "suggestions": [
                    {
                        "type": "subscription_cancel",
                        "title": "Consolidate Entertainment Subscriptions",
                        "detail": "Multiple recurring digital subscriptions detected. Pausing unused services could reduce monthly recurring expenses.",
                        "estimated_saving_minor": 79900,  # ₹799.00
                    },
                    {
                        "type": "dining_reduction",
                        "title": "Optimize Weekday Food Delivery",
                        "detail": "High frequency of convenience food orders observed. Cooking mid-week dinners can preserve disposable cashflow.",
                        "estimated_saving_minor": 250000,  # ₹2,500.00
                    },
                    {
                        "type": "utility_audit",
                        "title": "Audit Home Electricity & Internet",
                        "detail": "Utility outlays have risen over recent months compared to average seasonal baselines.",
                        "estimated_saving_minor": 85000,  # ₹850.00
                    },
                ],
                "disclaimer": "These suggestions are automated algorithmic estimates for budgeting guidance, not certified financial advice.",
            }

        # 3. Default structured response
        return {"response": "Mock LLM processed structured request successfully.", "success": True}


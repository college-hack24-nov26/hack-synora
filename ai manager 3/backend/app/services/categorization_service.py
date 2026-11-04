import re
import uuid
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.models import Category, MerchantRule, Transaction, AuditLog
from app.services.consent_service import has_active_consent
from app.services.llm.factory import get_llm_client, check_user_daily_ai_limit
from app.services.llm.client import LLMError


class CategorizationResult(BaseModel):
    category_id: Optional[str] = None
    category_name: str = "Uncategorized"
    category_source: str = "rule"  # rule, ml, user
    category_confidence: float = 1.0
    needs_review: bool = False
    matched_rule_id: Optional[str] = None


# In-memory merchant classification cache (normalized_merchant -> (category_name, confidence))
_MERCHANT_AI_CACHE: Dict[str, Tuple[str, float]] = {}


def get_amount_bucket(amount_minor: int) -> str:
    """Classifies an amount into standard privacy-preserving privacy brackets."""
    if amount_minor < 50000:
        return "< ₹500"
    elif amount_minor <= 200000:
        return "₹500 - ₹2,000"
    elif amount_minor <= 1000000:
        return "₹2,000 - ₹10,000"
    else:
        return "> ₹10,000"


# Built-in keyword patterns for common Indian merchants and UPI payment descriptors
BUILTIN_RULES: List[Tuple[str, str, List[str]]] = [
    (
        "Food & Dining",
        "food",
        [
            r"\bswiggy\b",
            r"\bzomato\b",
            r"\bstarbucks\b",
            r"\bmcdonalds?\b",
            r"\bkfc\b",
            r"\bdominos?\b",
            r"\bpizza\s*hut\b",
            r"\bsubway\b",
            r"\bburger\s*king\b",
            r"\bchaayos\b",
            r"\bchai\s*point\b",
            r"\bhaldirams?\b",
            r"\bbarbeque\s*nation\b",
            r"\bdineout\b",
            r"\brestaurant\b",
            r"\bcafe\b",
            r"\bbakery\b",
            r"\beatclub\b",
            r"\bfreshmenu\b",
        ],
    ),
    (
        "Groceries",
        "shopping-cart",
        [
            r"\bblinkit\b",
            r"\bzepto\b",
            r"\binstamart\b",
            r"\bbigbasket\b",
            r"\bbb\s*daily\b",
            r"\bdmart\b",
            r"\bspencers?\b",
            r"\bnature'?s\s*basket\b",
            r"\bmilkbasket\b",
            r"\breliance\s*fresh\b",
            r"\breliance\s*smart\b",
            r"\bgrocery\b",
            r"\bsupermarket\b",
            r"\bkirana\b",
            r"\bfruits?\b",
            r"\bvegetables?\b",
        ],
    ),
    (
        "Travel & Commute",
        "car",
        [
            r"\buber\b",
            r"\bola\b",
            r"\brapido\b",
            r"\birctc\b",
            r"\bmakemytrip\b",
            r"\bgoibibo\b",
            r"\beasemytrip\b",
            r"\bindigo\b",
            r"\bair\s*india\b",
            r"\bvistara\b",
            r"\bakasa\b",
            r"\bspicejet\b",
            r"\bmetro\b",
            r"\bbmtc\b",
            r"\bdtc\b",
            r"\bfastag\b",
            r"\btoll\b",
            r"\bpetrol\b",
            r"\bfuel\b",
            r"\bhpcl\b",
            r"\bbpcl\b",
            r"\biocl\b",
            r"\bshell\b",
        ],
    ),
    (
        "Shopping & E-Commerce",
        "shopping-bag",
        [
            r"\bamazon\b",
            r"\bflipkart\b",
            r"\bmyntra\b",
            r"\bajio\b",
            r"\bmeesho\b",
            r"\bnykaa\b",
            r"\btata\s*cliq\b",
            r"\bzara\b",
            r"\bh&m\b",
            r"\bcroma\b",
            r"\breliance\s*digital\b",
            r"\bdecathlon\b",
            r"\bikea\b",
            r"\buniqlo\b",
        ],
    ),
    (
        "Bills & Utilities",
        "zap",
        [
            r"\belectricity\b",
            r"\bbescom\b",
            r"\btneb\b",
            r"\bmseb\b",
            r"\bcesc\b",
            r"\btata\s*power\b",
            r"\badani\s*electricity\b",
            r"\bpiped\s*gas\b",
            r"\bindane\b",
            r"\bhp\s*gas\b",
            r"\bbharat\s*gas\b",
            r"\bairtel\b",
            r"\bjio\b",
            r"\bvodafone\b",
            r"\bvi\b",
            r"\bbsnl\b",
            r"\bact\s*fibernet\b",
            r"\bbroadband\b",
            r"\bwifi\b",
            r"\bdth\b",
            r"\btata\s*play\b",
            r"\bdishtv\b",
            r"\bwater\s*bill\b",
            r"\bmunicipal\b",
            r"\bbilldesk\b",
        ],
    ),
    (
        "Entertainment",
        "film",
        [
            r"\bnetflix\b",
            r"\bspotify\b",
            r"\bhotstar\b",
            r"\bdisney\b",
            r"\bprime\s*video\b",
            r"\byoutube\b",
            r"\bbookmyshow\b",
            r"\bpvr\b",
            r"\binox\b",
            r"\bcinepolis\b",
            r"\bsony\s*liv\b",
            r"\bzee5\b",
            r"\bapple\s*music\b",
            r"\bgaana\b",
            r"\bplaystation\b",
        ],
    ),
    (
        "Healthcare & Medical",
        "heart-pulse",
        [
            r"\bapollo\b",
            r"\b1mg\b",
            r"\bpharmeasy\b",
            r"\bnetmeds\b",
            r"\bmedplus\b",
            r"\bmax\s*healthcare\b",
            r"\bfortis\b",
            r"\bmanipal\b",
            r"\bhospital\b",
            r"\bclinic\b",
            r"\bdiagnostic\b",
            r"\blal\s*pathlabs\b",
            r"\bpharmacy\b",
            r"\bchemist\b",
        ],
    ),
    (
        "Investments & Savings",
        "trending-up",
        [
            r"\bzerodha\b",
            r"\bgroww\b",
            r"\bupstox\b",
            r"\bangel\s*one\b",
            r"\bkuvera\b",
            r"\bcoin\b",
            r"\bindmoney\b",
            r"\bmutual\s*fund\b",
            r"\bsip\b",
            r"\bnps\b",
            r"\bppf\b",
            r"\bfixed\s*deposit\b",
        ],
    ),
    (
        "Salary & Payroll",
        "dollar-sign",
        [
            r"\bsalary\b",
            r"\bpayroll\b",
            r"\bdirect\s*dep\b",
            r"\bdividend\b",
            r"\binterest\s*credit\b",
        ],
    ),
]


def sanitize_minimal_model_payload(
    merchant: Optional[str],
    description: Optional[str],
    amount_minor: int,
    direction: str,
) -> Dict[str, Any]:
    """Promise 2 & Categorization Privacy:

    Send ONLY minimal data: normalized merchant, description, amount,
    direction.
    NEVER include names, account numbers, card numbers, or balances.
    """
    clean_merchant = (merchant or "").strip()
    clean_desc = (description or "").strip()

    # Redact any card masks (••••1234), account numbers or long digit sequences
    clean_merchant = re.sub(r"(?:[•*X\d]{4,})", "[REDACTED_NUM]", clean_merchant)
    clean_desc = re.sub(r"(?:[•*X\d]{4,})", "[REDACTED_NUM]", clean_desc)

    # Strip balance disclosures if accidentally present
    clean_desc = re.sub(
        r"(?i)(?:avl\s*bal|balance|avlbl\s*bal)[\s:INRrs.\d,]+", "", clean_desc
    ).strip()

    return {
        "merchant": clean_merchant,
        "description": clean_desc,
        "amount": round(amount_minor / 100, 2),
        "direction": direction,
    }


def predict_with_text_classifier(
    minimal_data: Dict[str, Any],
) -> Tuple[Optional[str], float]:
    """Lightweight deterministic model-based suggestion fallback.

    Returns (suggested_category_name, confidence).
    """
    combined = f"{minimal_data.get('merchant', '')} {minimal_data.get('description', '')}".lower()

    # Known domain patterns for ML classification
    ml_patterns = [
        (
            "Healthcare & Medical",
            0.85,
            [
                "dentist",
                "dental",
                "physiotherapy",
                "pediatric",
                "optician",
                "lenskart",
            ],
        ),
        (
            "Education",
            0.88,
            [
                "udemy",
                "coursera",
                "edx",
                "tutor",
                "tuition",
                "school",
                "college",
                "university",
                "course",
            ],
        ),
        (
            "Fitness & Sports",
            0.85,
            ["cult.fit", "curefit", "gym", "fitness", "aerobics", "badminton", "crossfit"],
        ),
        (
            "Software & Tech",
            0.85,
            [
                "aws",
                "github",
                "jetbrains",
                "openai",
                "digitalocean",
                "cloudflare",
                "godaddy",
                "hosting",
            ],
        ),
        (
            "Home & Rent",
            0.80,
            ["maintenance", "society", "mygate", "nobroker", "apartment maintenance", "rent"],
        ),
        (
            "Personal Care",
            0.75,
            ["salon", "spa", "barber", "enrich", "jawed habib", "urban company salon"],
        ),
    ]

    for cat_name, conf, keywords in ml_patterns:
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", combined):
                return cat_name, conf

    # If ambiguous, unfamiliar, or low-information tokens:
    # return low confidence (< 0.6) so it gets flagged as "needs review"
    ambiguous_tokens = ["unknown", "corp", "misc", "charge", "transfer", "random", "pos", "ecom"]
    for tok in ambiguous_tokens:
        if tok in combined:
            return "Uncategorized", 0.40

    # Default low-confidence fallback for unseen merchants
    return "Uncategorized", 0.35


async def get_system_and_user_category_map(
    db: AsyncSession, user_id: str
) -> Tuple[Dict[str, str], Optional[str]]:
    """Returns a lookup dict {category_name_lower: category_id} and the

    uncategorized_id.
    """
    stmt = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == user_id)
    )
    res = await db.execute(stmt)
    categories = res.scalars().all()

    cat_map: Dict[str, str] = {}
    uncategorized_id: Optional[str] = None

    for c in categories:
        name_lower = c.name.strip().lower()
        cat_map[name_lower] = c.id
        if "uncategorized" in name_lower and not uncategorized_id:
            uncategorized_id = c.id

    # Fallback uncategorized if none explicitly found
    if not uncategorized_id and categories:
        uncategorized_id = categories[0].id

    return cat_map, uncategorized_id


def resolve_category_id_from_name(
    name: str, cat_map: Dict[str, str], uncategorized_id: Optional[str]
) -> Optional[str]:
    """Finds the best matching category ID from the map using exact or fuzzy

    keyword matching.
    """
    name_clean = name.strip().lower()
    if name_clean in cat_map:
        return cat_map[name_clean]

    # Partial substring match (e.g. "Food" in "Food & Dining")
    for key, cid in cat_map.items():
        if name_clean in key or key in name_clean:
            return cid

    return uncategorized_id


async def categorize_transaction_data(
    db: AsyncSession,
    user_id: str,
    merchant: Optional[str],
    description: Optional[str],
    amount_minor: int,
    direction: str,
) -> CategorizationResult:
    """Core 3-Step Categorization Engine:

    1. Step 1: Predefined rules:
       - User's own MerchantRule patterns (highest priority)
       - Built-in keyword / UPI merchant patterns
       -> Sets category_source="rule", confidence=1.0, needs_review=False
    2. Step 2: Model-based suggestion:
       - Pluggable ML classifier (minimal non-PII data only)
       - If confidence >= 0.6 -> category_source="ml", needs_review=False
       - If confidence < 0.6 -> category_source="ml", needs_review=True, Uncategorized
    3. Step 3: User correction wins:
       - Handled when user updates category via PATCH /transactions/{id}.
    """
    cat_map, uncategorized_id = await get_system_and_user_category_map(db, user_id)

    raw_text = f"{merchant or ''} {description or ''}".strip().lower()

    # -------------------------------------------------------------
    # Step 1A: Check User's own MerchantRules (Highest Priority)
    # -------------------------------------------------------------
    user_rules_stmt = (
        select(MerchantRule)
        .where(MerchantRule.user_id == user_id)
        .order_by(MerchantRule.priority.desc(), MerchantRule.created_at.desc())
    )
    user_rules_res = await db.execute(user_rules_stmt)
    user_rules = user_rules_res.scalars().all()

    for rule in user_rules:
        pattern = rule.pattern.strip().lower()
        # Test regex or substring match
        matched = False
        try:
            if re.search(pattern, raw_text, re.IGNORECASE):
                matched = True
        except re.error:
            if pattern in raw_text:
                matched = True

        if matched:
            cat_obj = await db.get(Category, rule.category_id)
            cat_name = cat_obj.name if cat_obj else "Custom Category"
            return CategorizationResult(
                category_id=rule.category_id,
                category_name=cat_name,
                category_source="rule",
                category_confidence=1.0,
                needs_review=False,
                matched_rule_id=rule.id,
            )

    # -------------------------------------------------------------
    # Step 1B: Check Built-in Indian Merchant & UPI Rules
    # -------------------------------------------------------------
    for target_cat_name, icon, patterns in BUILTIN_RULES:
        for pat in patterns:
            if re.search(pat, raw_text, re.IGNORECASE):
                cid = resolve_category_id_from_name(target_cat_name, cat_map, uncategorized_id)
                return CategorizationResult(
                    category_id=cid,
                    category_name=target_cat_name,
                    category_source="rule",
                    category_confidence=1.0,
                    needs_review=False,
                )

    # -------------------------------------------------------------
    # Step 2: Model-Based Suggestion (Pluggable LLM / Classifier)
    # -------------------------------------------------------------
    clean_merchant_key = (merchant or "").strip().lower()
    minimal_payload = sanitize_minimal_model_payload(
        merchant=merchant,
        description=description,
        amount_minor=amount_minor,
        direction=direction,
    )
    amount_bucket = get_amount_bucket(amount_minor)
    
    # Check cache first for instant resolution without network or API costs
    if clean_merchant_key and clean_merchant_key in _MERCHANT_AI_CACHE:
        cached_cat, cached_conf = _MERCHANT_AI_CACHE[clean_merchant_key]
        if cached_conf >= 0.6 and cached_cat != "Uncategorized":
            cid = resolve_category_id_from_name(cached_cat, cat_map, uncategorized_id)
            return CategorizationResult(
                category_id=cid,
                category_name=cached_cat,
                category_source="ml",
                category_confidence=cached_conf,
                needs_review=False,
            )

    # Privacy & Consent Check: User MUST have granted active "ai_processing" consent
    has_ai_consent = await has_active_consent(db, user_id, "ai_processing")
    if not has_ai_consent:
        # Fall back to deterministic on-premise text classifier (no third-party data transmission)
        model_cat_name, model_confidence = predict_with_text_classifier(minimal_payload)
        if model_confidence >= 0.6 and model_cat_name and model_cat_name != "Uncategorized":
            cid = resolve_category_id_from_name(model_cat_name, cat_map, uncategorized_id)
            return CategorizationResult(
                category_id=cid,
                category_name=model_cat_name,
                category_source="ml",
                category_confidence=model_confidence,
                needs_review=False,
            )
        else:
            return CategorizationResult(
                category_id=uncategorized_id,
                category_name="Uncategorized",
                category_source="ml",
                category_confidence=model_confidence,
                needs_review=True,
            )

    # Check daily limit per user
    try:
        await check_user_daily_ai_limit(user_id)
    except Exception:
        # On quota exhaustion, fall back to review without failing transaction import
        return CategorizationResult(
            category_id=uncategorized_id,
            category_name="Uncategorized",
            category_source="ml",
            category_confidence=0.0,
            needs_review=True,
        )

    model_cat_name: Optional[str] = None
    model_confidence: float = 0.0

    try:
        llm = get_llm_client()
        allowed_cats = list(cat_map.keys())
        system_prompt = (
            "You are an expert Indian personal finance categorization engine. "
            "Categorize the transaction strictly based on the normalized merchant and description into one of the allowed categories. "
            "Output pure JSON matching: {\"results\": [{\"id\": \"1\", \"category\": \"<Category>\", \"confidence\": <float 0.0 to 1.0>}]}. "
            "If ambiguous or unfamiliar, return confidence < 0.6."
        )
        user_prompt = (
            f"Allowed categories: {allowed_cats}\n"
            f"Transaction to categorize: [{{\"id\": \"1\", \"merchant\": \"{minimal_payload['merchant']}\", "
            f"\"description\": \"{minimal_payload['description']}\", \"amount_range\": \"{amount_bucket}\", "
            f"\"direction\": \"{direction}\"}}]"
        )

        res = await llm.complete_json(
            system=system_prompt,
            user=user_prompt,
            max_tokens=300,
            temperature=0.1,
            model_tier="fast",
        )

        results_list = res.get("results", [])
        if results_list and isinstance(results_list, list):
            model_cat_name = results_list[0].get("category")
            model_confidence = float(results_list[0].get("confidence", 0.5))
        else:
            model_cat_name, model_confidence = predict_with_text_classifier(minimal_payload)
    except Exception:
        # Fallback to local deterministic classifier on any upstream LLM error
        model_cat_name, model_confidence = predict_with_text_classifier(minimal_payload)

    # Cache result if merchant exists
    if clean_merchant_key and model_cat_name:
        _MERCHANT_AI_CACHE[clean_merchant_key] = (model_cat_name, model_confidence)

    # Check Confidence Threshold (0.6)
    if model_confidence >= 0.6 and model_cat_name and model_cat_name != "Uncategorized":
        cid = resolve_category_id_from_name(model_cat_name, cat_map, uncategorized_id)
        return CategorizationResult(
            category_id=cid,
            category_name=model_cat_name,
            category_source="ml",
            category_confidence=model_confidence,
            needs_review=False,
        )
    else:
        # Low confidence (< 0.6) or unknown -> Mark as "needs review" and assign Uncategorized
        return CategorizationResult(
            category_id=uncategorized_id,
            category_name="Uncategorized",
            category_source="ml",
            category_confidence=model_confidence,
            needs_review=True,
        )


async def batch_categorize_transactions(
    db: AsyncSession,
    user_id: str,
    items: List[Dict[str, Any]],
) -> List[CategorizationResult]:
    """
    Batches categorization up to 20 transactions per LLM call.
    1. Checks user rules, built-in rules, and in-memory merchant cache.
    2. Sends remaining items in chunks of up to 20 to the fast LLM tier.
    """
    cat_map, uncategorized_id = await get_system_and_user_category_map(db, user_id)
    
    # Pre-fetch user rules
    user_rules_stmt = (
        select(MerchantRule)
        .where(MerchantRule.user_id == user_id)
        .order_by(MerchantRule.priority.desc(), MerchantRule.created_at.desc())
    )
    user_rules_res = await db.execute(user_rules_stmt)
    user_rules = user_rules_res.scalars().all()

    results: List[Optional[CategorizationResult]] = [None] * len(items)
    pending_ai_indices: List[int] = []

    for idx, it in enumerate(items):
        merchant = it.get("merchant_normalized") or it.get("merchant_raw") or ""
        desc = it.get("description") or ""
        raw_text = f"{merchant} {desc}".strip().lower()

        # Step 1A: User rules
        matched_user = False
        for rule in user_rules:
            pattern = rule.pattern.strip().lower()
            try:
                if re.search(pattern, raw_text, re.IGNORECASE):
                    matched_user = True
            except re.error:
                if pattern in raw_text:
                    matched_user = True
            if matched_user:
                cat_obj = await db.get(Category, rule.category_id)
                cat_name = cat_obj.name if cat_obj else "Custom Category"
                results[idx] = CategorizationResult(
                    category_id=rule.category_id,
                    category_name=cat_name,
                    category_source="rule",
                    category_confidence=1.0,
                    needs_review=False,
                    matched_rule_id=rule.id,
                )
                break
        if matched_user:
            continue

        # Step 1B: Built-in rules
        matched_builtin = False
        for target_cat_name, icon, patterns in BUILTIN_RULES:
            for pat in patterns:
                if re.search(pat, raw_text, re.IGNORECASE):
                    cid = resolve_category_id_from_name(target_cat_name, cat_map, uncategorized_id)
                    results[idx] = CategorizationResult(
                        category_id=cid,
                        category_name=target_cat_name,
                        category_source="rule",
                        category_confidence=1.0,
                        needs_review=False,
                    )
                    matched_builtin = True
                    break
            if matched_builtin:
                break
        if matched_builtin:
            continue

        # Check Cache
        clean_merchant = merchant.strip().lower()
        if clean_merchant and clean_merchant in _MERCHANT_AI_CACHE:
            cached_cat, cached_conf = _MERCHANT_AI_CACHE[clean_merchant]
            if cached_conf >= 0.6 and cached_cat != "Uncategorized":
                cid = resolve_category_id_from_name(cached_cat, cat_map, uncategorized_id)
                results[idx] = CategorizationResult(
                    category_id=cid,
                    category_name=cached_cat,
                    category_source="ml",
                    category_confidence=cached_conf,
                    needs_review=False,
                )
                continue

        pending_ai_indices.append(idx)

    if not pending_ai_indices:
        return [r for r in results if r is not None]

    # Consent check for AI batch
    has_ai_consent = await has_active_consent(db, user_id, "ai_processing")
    if not has_ai_consent:
        for idx in pending_ai_indices:
            results[idx] = CategorizationResult(
                category_id=uncategorized_id,
                category_name="Uncategorized",
                category_source="ml",
                category_confidence=0.0,
                needs_review=True,
            )
        return [r for r in results if r is not None]

    # Process pending items in batches of up to 20
    llm = get_llm_client()
    allowed_cats = list(cat_map.keys())
    batch_size = 20

    for i in range(0, len(pending_ai_indices), batch_size):
        chunk_indices = pending_ai_indices[i : i + batch_size]
        chunk_payload = []
        for c_idx in chunk_indices:
            it = items[c_idx]
            min_p = sanitize_minimal_model_payload(
                merchant=it.get("merchant_normalized") or it.get("merchant_raw"),
                description=it.get("description"),
                amount_minor=it.get("amount_minor", 0),
                direction=it.get("direction", "debit"),
            )
            bucket = get_amount_bucket(it.get("amount_minor", 0))
            chunk_payload.append({
                "id": str(c_idx),
                "merchant": min_p["merchant"],
                "description": min_p["description"],
                "amount_range": bucket,
                "direction": min_p["direction"],
            })

        try:
            await check_user_daily_ai_limit(user_id)
            system_prompt = (
                "You are an expert Indian personal finance categorization engine. "
                "Categorize each transaction in the batch into one of the allowed categories. "
                "Output strictly valid JSON with key 'results': "
                "[{\"id\": \"<id>\", \"category\": \"<Category>\", \"confidence\": <float 0.0 to 1.0>}]."
            )
            user_prompt = (
                f"Allowed categories: {allowed_cats}\n"
                f"Transactions: {chunk_payload}"
            )
            llm_res = await llm.complete_json(
                system=system_prompt,
                user=user_prompt,
                max_tokens=1000,
                temperature=0.1,
                model_tier="fast",
            )
            pred_map = {str(item["id"]): item for item in llm_res.get("results", []) if "id" in item}
        except Exception:
            pred_map = {}

        for c_idx in chunk_indices:
            it = items[c_idx]
            clean_merchant = (it.get("merchant_normalized") or it.get("merchant_raw") or "").strip().lower()
            prediction = pred_map.get(str(c_idx))
            if prediction:
                cat_name = prediction.get("category", "Uncategorized")
                conf = float(prediction.get("confidence", 0.5))
            else:
                # Deterministic fallback
                min_p = sanitize_minimal_model_payload(
                    merchant=it.get("merchant_normalized") or it.get("merchant_raw"),
                    description=it.get("description"),
                    amount_minor=it.get("amount_minor", 0),
                    direction=it.get("direction", "debit"),
                )
                cat_name, conf = predict_with_text_classifier(min_p)

            if clean_merchant:
                _MERCHANT_AI_CACHE[clean_merchant] = (cat_name, conf)

            if conf >= 0.6 and cat_name != "Uncategorized":
                cid = resolve_category_id_from_name(cat_name, cat_map, uncategorized_id)
                results[c_idx] = CategorizationResult(
                    category_id=cid,
                    category_name=cat_name,
                    category_source="ml",
                    category_confidence=conf,
                    needs_review=False,
                )
            else:
                results[c_idx] = CategorizationResult(
                    category_id=uncategorized_id,
                    category_name="Uncategorized",
                    category_source="ml",
                    category_confidence=conf,
                    needs_review=True,
                )

    return [r for r in results if r is not None]


async def recategorize_user_transactions(
    db: AsyncSession,
    user_id: str,
    only_needs_review: bool = False,
) -> Dict[str, Any]:
    """Re-runs categorization for a user's own transactions (e.g.

    after rule additions or edits). User-corrected transactions
    (category_source="user") are preserved unless forced.
    """
    conditions = [
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
        Transaction.category_source != "user",  # User corrections always win!
    ]

    if only_needs_review:
        conditions.append(Transaction.needs_review == True)

    stmt = select(Transaction).where(and_(*conditions))
    res = await db.execute(stmt)
    txns = res.scalars().all()

    updated_count = 0
    now_needs_review_count = 0

    for txn in txns:
        result = await categorize_transaction_data(
            db=db,
            user_id=user_id,
            merchant=txn.merchant_normalized or txn.merchant_raw,
            description=txn.description,
            amount_minor=txn.amount_minor,
            direction=txn.direction,
        )

        txn.category_id = result.category_id
        txn.category_source = result.category_source
        txn.category_confidence = result.category_confidence
        txn.needs_review = result.needs_review

        updated_count += 1
        if result.needs_review:
            now_needs_review_count += 1

    await db.commit()

    return {
        "total_evaluated": len(txns),
        "updated_count": updated_count,
        "needs_review_count": now_needs_review_count,
    }


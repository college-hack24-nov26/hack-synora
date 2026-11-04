import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple


# Common Indian Merchant Normalization Mapping
MERCHANT_MAP = {
    r"(?i)swiggy": ("Swiggy", "Food & Dining"),
    r"(?i)zomato": ("Zomato", "Food & Dining"),
    r"(?i)mcdonald|kfc|domino|starbucks|subway|burger king|pizza hut|chai point": ("Dining Out", "Food & Dining"),
    r"(?i)zepto|blinkit|bigbasket|instamart|dmart|nature basket": ("Grocery Store", "Groceries"),
    r"(?i)uber|ola|rapido|namma yatri": ("Ride Share", "Transport"),
    r"(?i)indian oil|bharat petro|hpcl|iocl|shell|petrol": ("Fuel Station", "Fuel"),
    r"(?i)amazon|flipkart|myntra|ajio|meesho|tata cliq": ("Online Shopping", "Shopping"),
    r"(?i)netflix|spotify|hotstar|prime video|youtube|apple\.com": ("Digital Subscription", "Subscriptions"),
    r"(?i)airtel|jio|vi |vodafone|bescom|tneb|mahadiscom|tata power|adani electricity": ("Utility Provider", "Bills & Utilities"),
    r"(?i)salary|payroll|stipend|wages": ("Employer", "Salary"),
    r"(?i)atm|cash wdl|cash withdrawal": ("Cash ATM", "Cash Withdrawal"),
    r"(?i)zerodha|groww|upstox|kuvera|mf central|coin": ("Investment Platform", "Investments"),
    r"(?i)hdfc ergo|lic|star health|max life|tata aia": ("Insurance Provider", "Insurance"),
    r"(?i)emi|loan|cred club|cred": ("EMI / Credit Card Bill", "EMI/Loans"),
}

# Bank Regex Templates for Indian Banks & UPI
BANK_TEMPLATES = [
    # HDFC SMS: "HDFC Bank: Rs 849.00 debited from a/c **4589 on 03-Nov-26 to SWIGGY. Avl bal: Rs 42,150.00."
    {
        "name": "HDFC",
        "pattern": re.compile(
            r"(?i)(?:hdfc bank|hdfcbk).*?(?:rs\.?|inr)\s*([\d,]+\.?\d*)\s+(debited|credited).*?(?:a/c|account)\s*[*xX]*(\d{4}).*?(?:on|at)\s+([0-9a-zA-Z\s\-:]+?)(?:\s+to|\s+by|\s+towards|\s+at|\s+info:?)\s+([^.]+?)(?:\.|\s+avl bal|\s+ref)",
        ),
        "amount_idx": 1,
        "direction_idx": 2,
        "last4_idx": 3,
        "date_idx": 4,
        "merchant_idx": 5,
    },
    # SBI SMS: "Dear SBI User, your A/C 9901 debited by Rs 1500.00 on 02-Nov-26 by UPI/3310029/UBER."
    {
        "name": "SBI",
        "pattern": re.compile(
            r"(?i)(?:sbi|state bank).*?(?:a/c|acct|account)\s*[*xX]*(\d{4})\s+(debited|credited).*?(?:rs\.?|inr)\s*([\d,]+\.?\d*).*?(?:on|at)\s+([0-9a-zA-Z\s\-:]+?)(?:\s+by|\s+to|\s+towards|\s+at|\s+transfer to)\s+([^.]+?)(?:\.|\s+avl|\s+ref|$)",
        ),
        "amount_idx": 3,
        "direction_idx": 2,
        "last4_idx": 1,
        "date_idx": 4,
        "merchant_idx": 5,
    },
    # ICICI SMS: "ICICI Bank: Acct XX1204 debited with INR 2,499.00 on 01-Nov-26 towards AMAZON PAY."
    {
        "name": "ICICI",
        "pattern": re.compile(
            r"(?i)(?:icici bank|icicib).*?(?:a/c|acct|account)\s*[*xX]*(\d{4})\s+(debited|credited).*?(?:rs\.?|inr)\s*([\d,]+\.?\d*).*?(?:on|at)\s+([0-9a-zA-Z\s\-:]+?)(?:\s+by|\s+to|\s+towards|\s+at)\s+([^.]+?)(?:\.|\s+avl|\s+ref|$)",
        ),
        "amount_idx": 3,
        "direction_idx": 2,
        "last4_idx": 1,
        "date_idx": 4,
        "merchant_idx": 5,
    },
    # Axis / Kotak / Standard UPI SMS:
    {
        "name": "Axis_Kotak_UPI",
        "pattern": re.compile(
            r"(?i)(?:rs\.?|inr)\s*([\d,]+\.?\d*)\s+(debited|credited).*?(?:a/c|account|card)?\s*[*xX]*(\d{4})?.*?(?:to|by|towards|at|vpa|for)\s+([^.]+?)(?:\s+on|\s+at|\s+avl|\.|$)",
        ),
        "amount_idx": 1,
        "direction_idx": 2,
        "last4_idx": 3,
        "merchant_idx": 4,
        "date_idx": None,
    },
    # Generic UPI Pattern: "Paid Rs. 250 to Chai Point via PhonePe/GooglePay"
    {
        "name": "Generic_UPI",
        "pattern": re.compile(
            r"(?i)(?:paid|sent|transferred)\s+(?:rs\.?|inr)?\s*([\d,]+\.?\d*)\s+(?:to|towards)\s+([^.]+?)(?:\s+via|\s+using|\s+on|\.|$)",
        ),
        "amount_idx": 1,
        "direction_idx": "debit",
        "last4_idx": None,
        "merchant_idx": 2,
        "date_idx": None,
    },
    # Generic Credit Pattern: "Received Rs. 5000 from Client via UPI"
    {
        "name": "Generic_Credit",
        "pattern": re.compile(
            r"(?i)(?:received|credited)\s+(?:rs\.?|inr)?\s*([\d,]+\.?\d*)\s+(?:from|by)\s+([^.]+?)(?:\s+via|\s+on|\.|$)",
        ),
        "amount_idx": 1,
        "direction_idx": "credit",
        "last4_idx": None,
        "merchant_idx": 2,
        "date_idx": None,
    },
]


def clean_amount_to_minor(amount_str: str) -> int:
    """Converts '1,23,456.50' or '550' into integer paise."""
    cleaned = re.sub(r"[^\d.]", "", amount_str)
    try:
        val = float(cleaned)
        return int(round(val * 100))
    except Exception:
        return 0


def normalize_merchant_and_category(raw_merchant: str) -> Tuple[str, str]:
    raw_clean = re.sub(r"(?i)^(upi\/|vpa\/|ref\/|transfer to|payment to)\s*", "", raw_merchant).strip()
    raw_clean = re.sub(r"[\*#\-_]+", " ", raw_clean).strip()

    for pattern, (normalized_name, default_cat) in MERCHANT_MAP.items():
        if re.search(pattern, raw_clean):
            return normalized_name, default_cat

    # Capitalize words
    norm = " ".join(w.capitalize() for w in raw_clean.split()[:4])
    return norm if norm else "Unknown Payee", "Uncategorized"


def is_otp_or_promo(text: str) -> bool:
    """Filters out OTPs, promotional alerts, login verifications, and non-transaction messages."""
    otp_keywords = [
        r"(?i)\botp\b",
        r"(?i)one time password",
        r"(?i)verification code",
        r"(?i)security code",
        r"(?i)secret code",
        r"(?i)do not share",
        r"(?i)congratulations",
        r"(?i)discount",
        r"(?i)offer valid",
        r"(?i)apply now",
        r"(?i)pre-approved",
        r"(?i)cashback offer",
        r"(?i)reward points",
        r"(?i)loan approved",
        r"(?i)statement has been generated",
        r"(?i)your e-statement is attached",
        r"(?i)log ?in to your account",
    ]
    for kw in otp_keywords:
        if re.search(kw, text):
            return True
    return False


def sanitize_financial_text(text: str) -> str:
    """Promise 2: Data minimization.
    Strips balances, masks 12-19 digit card numbers, masks phone numbers in UPI VPAs.
    """
    if not text:
        return ""

    # Remove available balance statements
    sanitized = re.sub(
        r"(?i)(?:avl(?:\.|\s+)?bal(?:ance)?|available\s+bal(?:ance)?|tot(?:al)?\s+bal(?:ance)?)\s*(?::|is)?\s*(?:rs\.?|inr)?\s*[\d,]+\.?\d*",
        "",
        text,
    )

    # Mask credit/debit card numbers (12-19 digits)
    sanitized = re.sub(
        r"\b(?:\d{4}[ -]?){3}\d{4}\b|\b\d{13,19}\b",
        lambda m: "••••" + re.sub(r"\D", "", m.group())[-4:],
        sanitized,
    )

    # Mask 10-digit mobile numbers in UPI VPAs: e.g. 9876543210@okhdfcbank -> ••••••3210@okhdfcbank
    sanitized = re.sub(
        r"\b(\d{6})(\d{4})(@[a-zA-Z0-9]+)\b",
        r"••••••\2\3",
        sanitized,
    )

    # Clean double punctuation and collapse multiple whitespaces
    sanitized = re.sub(r"\.\s*\.", ".", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def mask_to_last4(val: Optional[str]) -> Optional[str]:
    """Ensures account/card numbers are never stored in raw form beyond last 4 digits."""
    if not val:
        return None
    digits = re.sub(r"\D", "", val)
    return digits[-4:] if len(digits) >= 4 else digits


def compute_dedupe_hash(account_id: str, date_iso: str, amount_minor: int, direction: str, description: str) -> str:
    raw = f"{account_id}|{date_iso}|{amount_minor}|{direction}|{description.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_single_sms(text: str, default_account_id: str) -> Optional[Dict[str, Any]]:
    clean_text = text.strip()
    if not clean_text or is_otp_or_promo(clean_text):
        return None

    for tpl in BANK_TEMPLATES:
        match = tpl["pattern"].search(clean_text)
        if match:
            # Extract amount
            amount_str = match.group(tpl["amount_idx"])
            amount_minor = clean_amount_to_minor(amount_str)
            if amount_minor <= 0:
                continue

            # Extract direction
            if isinstance(tpl["direction_idx"], str):
                direction = tpl["direction_idx"]
            else:
                dir_raw = match.group(tpl["direction_idx"]).lower()
                direction = "debit" if "debit" in dir_raw or "paid" in dir_raw else "credit"

            # Extract merchant
            merchant_raw = match.group(tpl["merchant_idx"]).strip() if tpl["merchant_idx"] else "Merchant"
            merchant_raw = sanitize_financial_text(merchant_raw)
            merchant_normalized, suggested_category = normalize_merchant_and_category(merchant_raw)

            # Extract last 4 (strictly masked)
            last4 = None
            if tpl.get("last4_idx") and match.group(tpl["last4_idx"]):
                last4 = mask_to_last4(match.group(tpl["last4_idx"]))

            # Extract or fallback Date
            now = datetime.now(timezone.utc)
            txn_date = now

            dedupe_hash = compute_dedupe_hash(
                default_account_id,
                txn_date.strftime("%Y-%m-%d"),
                amount_minor,
                direction,
                merchant_normalized,
            )

            return {
                "amount_minor": amount_minor,
                "direction": direction,
                "merchant_raw": merchant_raw,
                "merchant_normalized": merchant_normalized,
                "suggested_category": suggested_category,
                "last4": last4,
                "txn_date": txn_date,
                "description": f"SMS Alert: {merchant_normalized}",
                "dedupe_hash": dedupe_hash,
                "source": "sms",
            }

    return None


def parse_sms_batch(raw_blob: str, default_account_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    # Split by newlines or standard bank message delimiters
    chunks = [c.strip() for c in re.split(r"\n{2,}|\n(?=[A-Z0-9]{3,}|Dear|Rs\.|INR|Alert)", raw_blob) if c.strip()]
    if not chunks:
        chunks = [c.strip() for c in raw_blob.split("\n") if c.strip()]

    parsed = []
    errors = []

    for item in chunks:
        if is_otp_or_promo(item):
            continue
        res = parse_single_sms(item, default_account_id)
        if res:
            parsed.append(res)
        else:
            errors.append({
                "raw_text": sanitize_financial_text(item[:60]),
                "reason": "No matching bank SMS pattern found or non-transaction text",
            })

    return parsed, errors


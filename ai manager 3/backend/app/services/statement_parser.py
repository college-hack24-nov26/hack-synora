import io
import re
import csv
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from dateutil import parser as date_parser
import pdfplumber

from app.services.sms_parser import (
    clean_amount_to_minor,
    normalize_merchant_and_category,
    sanitize_financial_text,
    compute_dedupe_hash,
)
from app.core.errors import BadRequestException


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def parse_date_safe(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    cleaned = re.sub(r"[^\w\s/:\-]", "", date_str.strip())
    try:
        # Default dayfirst=True for Indian banking format (DD/MM/YYYY)
        dt = date_parser.parse(cleaned, dayfirst=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def parse_csv_statement(
    file_bytes: bytes,
    account_id: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Flexible CSV statement parser supporting multiple bank statement layouts."""
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception:
            raise BadRequestException("Unable to decode statement file. Please ensure it is a valid text/CSV file.")

    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        raise BadRequestException("The uploaded statement file is empty.")

    # Detect delimiter
    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = list(csv.reader(lines, delimiter=delimiter))
    if not reader:
        raise BadRequestException("No data rows found in CSV.")

    # Find the header row
    header_idx = -1
    date_col = -1
    desc_col = -1
    debit_col = -1
    credit_col = -1
    amount_col = -1
    type_col = -1

    for idx, row in enumerate(reader[:15]):
        lower_row = [c.lower().strip() for c in row]
        for col_idx, cell in enumerate(lower_row):
            if re.search(r"(?i)\b(date|txn date|transaction date|value date|posting date)\b", cell):
                date_col = col_idx
            elif re.search(r"(?i)\b(description|narration|particulars|remarks|details|merchant|payee)\b", cell):
                desc_col = col_idx
            elif re.search(r"(?i)\b(debit|dr|withdrawal|withdrawals|debit amount)\b", cell):
                debit_col = col_idx
            elif re.search(r"(?i)\b(credit|cr|deposit|deposits|credit amount)\b", cell):
                credit_col = col_idx
            elif re.search(r"(?i)\b(amount|txn amount|net amount|transaction amount)\b", cell):
                amount_col = col_idx
            elif re.search(r"(?i)\b(type|cr/dr|d/c|dr/cr|transaction type)\b", cell):
                type_col = col_idx

        # Check if we have minimum requirements: date and (debit/credit or amount)
        has_amount = (debit_col != -1 and credit_col != -1) or (amount_col != -1) or (debit_col != -1) or (credit_col != -1)
        if date_col != -1 and has_amount:
            header_idx = idx
            break

    # If no header was recognized, attempt positional defaults
    if header_idx == -1:
        date_col = 0
        desc_col = 1 if len(reader[0]) > 1 else 0
        if len(reader[0]) >= 4:
            debit_col = 2
            credit_col = 3
        elif len(reader[0]) >= 3:
            amount_col = 2
        header_idx = 0

    parsed: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for r_idx in range(header_idx + 1, len(reader)):
        row = reader[r_idx]
        if not row or all(not c.strip() for c in row):
            continue

        raw_snippet = " | ".join(row[:4])[:60]
        # Check date
        if date_col >= len(row):
            errors.append({"row": r_idx + 1, "raw_text": raw_snippet, "reason": "Missing date column"})
            continue

        date_val = parse_date_safe(row[date_col])
        if not date_val:
            # Maybe a summary row like "Total" or "Closing Balance"
            continue

        raw_desc = _clean_str(row[desc_col]) if desc_col != -1 and desc_col < len(row) else "Statement Spend"
        sanitized_desc = sanitize_financial_text(raw_desc) or "Statement Spend"
        merchant_normalized, suggested_category = normalize_merchant_and_category(sanitized_desc)

        amount_minor = 0
        direction = "debit"

        if debit_col != -1 and debit_col < len(row) and credit_col != -1 and credit_col < len(row):
            debit_str = row[debit_col].strip()
            credit_str = row[credit_col].strip()
            debit_val = clean_amount_to_minor(debit_str)
            credit_val = clean_amount_to_minor(credit_str)

            if debit_val > 0:
                amount_minor = debit_val
                direction = "debit"
            elif credit_val > 0:
                amount_minor = credit_val
                direction = "credit"
            else:
                continue
        elif amount_col != -1 and amount_col < len(row):
            amt_str = row[amount_col].strip()
            raw_amt = clean_amount_to_minor(amt_str)
            if raw_amt <= 0:
                continue
            amount_minor = raw_amt

            if type_col != -1 and type_col < len(row):
                t_str = row[type_col].lower().strip()
                if "cr" in t_str or "credit" in t_str or "deposit" in t_str:
                    direction = "credit"
                else:
                    direction = "debit"
            elif "-" in amt_str or "(" in amt_str:
                direction = "debit"
            else:
                direction = "debit"
        elif debit_col != -1 and debit_col < len(row):
            debit_val = clean_amount_to_minor(row[debit_col])
            if debit_val > 0:
                amount_minor = debit_val
                direction = "debit"
        elif credit_col != -1 and credit_col < len(row):
            credit_val = clean_amount_to_minor(row[credit_col])
            if credit_val > 0:
                amount_minor = credit_val
                direction = "credit"

        if amount_minor <= 0:
            errors.append({"row": r_idx + 1, "raw_text": raw_snippet, "reason": "No valid transaction amount found"})
            continue

        dedupe_hash = compute_dedupe_hash(
            account_id,
            date_val.strftime("%Y-%m-%d"),
            amount_minor,
            direction,
            merchant_normalized,
        )

        parsed.append({
            "amount_minor": amount_minor,
            "direction": direction,
            "merchant_raw": sanitized_desc,
            "merchant_normalized": merchant_normalized,
            "suggested_category": suggested_category,
            "last4": None,
            "txn_date": date_val,
            "description": f"Statement: {merchant_normalized}",
            "dedupe_hash": dedupe_hash,
            "source": "csv",
        })

    return parsed, errors


def parse_pdf_statement(
    file_bytes: bytes,
    account_id: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """In-memory PDF statement parser using pdfplumber."""
    try:
        pdf_file = io.BytesIO(file_bytes)
        with pdfplumber.open(pdf_file) as pdf:
            all_text = ""
            all_tables: List[List[List[str]]] = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        raise BadRequestException(f"Failed to read PDF file: {str(e)}")

    if len(all_text.strip()) < 30 and not all_tables:
        raise BadRequestException(
            "The uploaded PDF appears to be a scanned image or photo without selectable text. "
            "Please upload a digital text-based e-statement."
        )

    parsed: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    # First attempt: if structured tables were extracted from PDF
    if all_tables:
        for table in all_tables:
            if not table or len(table) < 2:
                continue

            header_idx = -1
            date_col = -1
            desc_col = -1
            debit_col = -1
            credit_col = -1
            amount_col = -1

            for row_idx, row in enumerate(table[:5]):
                if not row:
                    continue
                lower_row = [str(c or "").lower().strip() for c in row]
                for col_idx, cell in enumerate(lower_row):
                    if re.search(r"(?i)\b(date|txn date|value date)\b", cell):
                        date_col = col_idx
                    elif re.search(r"(?i)\b(description|narration|particulars|remarks|details)\b", cell):
                        desc_col = col_idx
                    elif re.search(r"(?i)\b(debit|dr|withdrawal|withdrawals)\b", cell):
                        debit_col = col_idx
                    elif re.search(r"(?i)\b(credit|cr|deposit|deposits)\b", cell):
                        credit_col = col_idx
                    elif re.search(r"(?i)\b(amount|net amount)\b", cell):
                        amount_col = col_idx

                if date_col != -1 and (debit_col != -1 or credit_col != -1 or amount_col != -1):
                    header_idx = row_idx
                    break

            if header_idx != -1:
                for row_idx in range(header_idx + 1, len(table)):
                    row = table[row_idx]
                    if not row or date_col >= len(row):
                        continue

                    dt = parse_date_safe(str(row[date_col] or ""))
                    if not dt:
                        continue

                    raw_desc = str(row[desc_col] or "").strip() if desc_col != -1 and desc_col < len(row) else "PDF Spend"
                    sanitized_desc = sanitize_financial_text(raw_desc) or "PDF Spend"
                    merchant_normalized, suggested_category = normalize_merchant_and_category(sanitized_desc)

                    amount_minor = 0
                    direction = "debit"

                    if debit_col != -1 and debit_col < len(row) and credit_col != -1 and credit_col < len(row):
                        d_val = clean_amount_to_minor(str(row[debit_col] or ""))
                        c_val = clean_amount_to_minor(str(row[credit_col] or ""))
                        if d_val > 0:
                            amount_minor = d_val
                            direction = "debit"
                        elif c_val > 0:
                            amount_minor = c_val
                            direction = "credit"
                    elif amount_col != -1 and amount_col < len(row):
                        amt = clean_amount_to_minor(str(row[amount_col] or ""))
                        if amt > 0:
                            amount_minor = amt
                            direction = "debit"

                    if amount_minor > 0:
                        dedupe_hash = compute_dedupe_hash(
                            account_id,
                            dt.strftime("%Y-%m-%d"),
                            amount_minor,
                            direction,
                            merchant_normalized,
                        )
                        parsed.append({
                            "amount_minor": amount_minor,
                            "direction": direction,
                            "merchant_raw": sanitized_desc,
                            "merchant_normalized": merchant_normalized,
                            "suggested_category": suggested_category,
                            "last4": None,
                            "txn_date": dt,
                            "description": f"PDF Statement: {merchant_normalized}",
                            "dedupe_hash": dedupe_hash,
                            "source": "pdf",
                        })

    # Second attempt: if table extraction was insufficient, parse lines via regex
    if not parsed:
        lines = [l.strip() for l in all_text.splitlines() if l.strip()]
        # Common line pattern: Date ... Description ... Amount (Dr/Cr)
        line_pattern = re.compile(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+((?:rs\.?|inr)?\s*[\d,]+\.\d{2})\s*(cr|dr|credit|debit)?",
            re.IGNORECASE,
        )

        for line in lines:
            m = line_pattern.search(line)
            if m:
                dt_str, desc_str, amt_str, dir_indicator = m.groups()
                dt = parse_date_safe(dt_str)
                amt_minor = clean_amount_to_minor(amt_str)
                if not dt or amt_minor <= 0:
                    continue

                direction = "credit" if dir_indicator and "cr" in dir_indicator.lower() else "debit"
                sanitized_desc = sanitize_financial_text(desc_str)
                merchant_normalized, suggested_category = normalize_merchant_and_category(sanitized_desc)

                dedupe_hash = compute_dedupe_hash(
                    account_id,
                    dt.strftime("%Y-%m-%d"),
                    amt_minor,
                    direction,
                    merchant_normalized,
                )
                parsed.append({
                    "amount_minor": amt_minor,
                    "direction": direction,
                    "merchant_raw": sanitized_desc,
                    "merchant_normalized": merchant_normalized,
                    "suggested_category": suggested_category,
                    "last4": None,
                    "txn_date": dt,
                    "description": f"PDF Statement: {merchant_normalized}",
                    "dedupe_hash": dedupe_hash,
                    "source": "pdf",
                })
            else:
                if any(k in line.lower() for k in ["paid", "transfer", "debit", "credit", "upi"]):
                    errors.append({
                        "raw_text": sanitize_financial_text(line[:60]),
                        "reason": "Could not extract standard bank transaction line",
                    })

    return parsed, errors


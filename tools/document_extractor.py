import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pypdf import PdfReader
from core.schemas import DocumentExtractionResult

# Patterns indicative of prompt injection attempts inside documents
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s*:\s*approve",
    r"you\s+must\s+approve",
    r"disregard\s+(the\s+)?(credit|debt|policy|rules)",
    r"override\s+underwriting\s+policy",
    r"assistant\s*:\s*sanction",
    r"admin\s+mode\s*:\s*enable",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[system\]",
    r"bypass\s+risk\s+check",
]


def sanitize_and_check_injection(text: str) -> Tuple[str, bool]:
    """Scan document text for prompt injection attempts and sanitize dangerous tokens."""
    injection_detected = False
    lower_text = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            injection_detected = True
            break

    # Strip dangerous control strings while preserving readable text
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return sanitized, injection_detected


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pypdf."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF document not found at: {pdf_path}")

    reader = PdfReader(str(path))
    extracted_pages = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        extracted_pages.append(page_text)

    return "\n".join(extracted_pages)


def parse_financial_fields_from_text(raw_text: str) -> DocumentExtractionResult:
    """
    Deterministically parses financial application attributes from extracted document text.
    Uses regex patterns to prevent hallucination or fabrication of missing data.
    """
    sanitized_text, injection_detected = sanitize_and_check_injection(raw_text)

    # Regex extractors
    name_match = re.search(
        r"(?:applicant(?:\s+name)?|employee\s+name|borrower|name)\s*[:=\-]\s*([A-Za-z\s\.\,\'\-]+?)(?:\n|\r|\t|;|$)",
        sanitized_text,
        re.IGNORECASE
    )

    income_match = re.search(
        r"(?:net\s+(?:monthly\s+)?(?:salary|income|pay)|monthly\s+(?:net\s+)?income)\s*[:=\-₹$Rs\.]*\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        sanitized_text,
        re.IGNORECASE
    )

    existing_emi_match = re.search(
        r"(?:existing\s+(?:monthly\s+)?emis?|current\s+(?:monthly\s+)?debts?|active\s+loan\s+emis?)\s*[:=\-₹$Rs\.]*\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        sanitized_text,
        re.IGNORECASE
    )

    loan_amount_match = re.search(
        r"(?:requested\s+(?:loan\s+)?amount|loan\s+amount\s+requested|principal\s+amount)\s*[:=\-₹$Rs\.]*\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        sanitized_text,
        re.IGNORECASE
    )

    tenure_match = re.search(
        r"(?:requested\s+tenure|tenure|term|repayment\s+period)\s*[:=\-]*\s*([0-9]{1,3})\s*(?:months?|m)",
        sanitized_text,
        re.IGNORECASE
    )

    rate_match = re.search(
        r"(?:interest\s+rate|annual\s+interest\s+rate|rate\s+of\s+interest)\s*[:=\-]*\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        sanitized_text,
        re.IGNORECASE
    )

    # Parsing values safely
    applicant_name = name_match.group(1).strip() if name_match else None
    if applicant_name and len(applicant_name) > 60:
        applicant_name = applicant_name[:60].strip()

    monthly_income = None
    if income_match:
        try:
            monthly_income = float(income_match.group(1).replace(",", ""))
        except ValueError:
            pass

    existing_emis = None
    if existing_emi_match:
        try:
            existing_emis = float(existing_emi_match.group(1).replace(",", ""))
        except ValueError:
            pass

    requested_amount = None
    if loan_amount_match:
        try:
            requested_amount = float(loan_amount_match.group(1).replace(",", ""))
        except ValueError:
            pass

    tenure_months = None
    if tenure_match:
        try:
            tenure_months = int(tenure_match.group(1))
        except ValueError:
            pass

    annual_interest_rate = None
    if rate_match:
        try:
            annual_interest_rate = float(rate_match.group(1))
        except ValueError:
            pass

    # Catalog missing essential fields
    missing_fields = []
    if not applicant_name:
        missing_fields.append("applicant_name")
    if monthly_income is None:
        missing_fields.append("monthly_income")
    if requested_amount is None:
        missing_fields.append("requested_amount")
    if tenure_months is None:
        missing_fields.append("tenure_months")

    notes_parts = []
    if injection_detected:
        notes_parts.append("WARNING: Potential adversarial prompt injection pattern detected and neutralized.")
    if missing_fields:
        notes_parts.append(f"Unidentified fields in document: {', '.join(missing_fields)}.")

    return DocumentExtractionResult(
        applicant_name=applicant_name,
        monthly_income=monthly_income,
        existing_emis=existing_emis,
        requested_amount=requested_amount,
        tenure_months=tenure_months,
        annual_interest_rate=annual_interest_rate,
        missing_fields=missing_fields,
        inconsistencies=[],
        validation_passed=not injection_detected and "monthly_income" not in missing_fields,
        prompt_injection_detected=injection_detected,
        notes=" ".join(notes_parts) if notes_parts else "Document parsed successfully."
    )


def reconcile_declared_vs_extracted(
    declared: Dict[str, Any],
    extracted: DocumentExtractionResult,
    tolerance_pct: float = 5.0
) -> List[str]:
    """
    Compare declared values from application form against extracted document figures.
    Returns list of discrepancies found.
    """
    inconsistencies = []

    # Income reconciliation
    if declared.get("monthly_income") is not None and extracted.monthly_income is not None:
        decl_income = float(declared["monthly_income"])
        ext_income = float(extracted.monthly_income)
        diff_pct = abs(decl_income - ext_income) / max(decl_income, 1.0) * 100.0
        if diff_pct > tolerance_pct:
            inconsistencies.append(
                f"Income discrepancy: Declared ₹{decl_income:,.2f} vs Document ₹{ext_income:,.2f} ({diff_pct:.1f}% variance)"
            )

    # Existing EMI reconciliation
    if declared.get("existing_emis") is not None and extracted.existing_emis is not None:
        decl_emi = float(declared["existing_emis"])
        ext_emi = float(extracted.existing_emis)
        if abs(decl_emi - ext_emi) > 500:
            inconsistencies.append(
                f"Existing EMI discrepancy: Declared ₹{decl_emi:,.2f} vs Document ₹{ext_emi:,.2f}"
            )

    return inconsistencies

from enum import Enum
from typing import NamedTuple


class FinalDecisionEnum(str, Enum):
    SANCTION = "SANCTION"
    DECLINE = "DECLINE"
    REFER = "REFER"


class AffordabilityVerdictEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REFER = "REFER"


class CreditVerdictEnum(str, Enum):
    PASS = "PASS"
    DECLINE = "DECLINE"
    REFER = "REFER"
    UNKNOWN = "UNKNOWN"


class UnderwritingPolicy:
    """Configurable credit and underwriting risk rules."""

    MAX_FOIR_PERCENT: float = 40.0
    MIN_LOAN_AMOUNT: float = 10000.0
    MAX_LOAN_AMOUNT: float = 10000000.0
    MIN_TENURE_MONTHS: int = 6
    MAX_TENURE_MONTHS: int = 84
    DEFAULT_INTEREST_RATE: float = 12.0

    # Decision descriptions
    REASON_INCOME_MISSING = "Monthly income is missing or unverified. Immediate halt and referral for manual verification required."
    REASON_CREDIT_FRAUD = "Verified fraud indicator identified in historical credit bureau records. Mandatory decline."
    REASON_CREDIT_DEFAULT = "Verified historical loan default identified in bureau records. Mandatory decline under hard risk policy."
    REASON_CREDIT_UNKNOWN = "No historical credit record exists for applicant. Referred for manual bureau onboarding and verification."
    REASON_CREDIT_DELINQUENT = "Unresolved delinquent accounts or past missed payments identified in bureau records. Referred for credit officer review."
    REASON_AFFORDABILITY_FAILED = "Proposed debt obligations exceed the maximum 40% FOIR threshold. Counter-offer evaluated."
    REASON_AFFORDABILITY_CRITICAL = "Existing debt obligations already exceed total affordability threshold. Unable to extend credit."
    REASON_SANCTION_APPROVED = "The applicant has verified income, repayment obligations are within the configured affordability limit (FOIR <= 40%), and credit history contains no identified red flags."
    REASON_DOCS_INCONSISTENT = "Discrepancy detected between self-declared application figures and extracted financial documentation. Referred for manual document audit."

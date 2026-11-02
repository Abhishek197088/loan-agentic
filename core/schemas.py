from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from core.policies import FinalDecisionEnum, AffordabilityVerdictEnum, CreditVerdictEnum


class LoanApplicationInput(BaseModel):
    """Initial loan application input received from user/API."""
    application_id: str = Field(..., min_length=1, description="Unique identifier for the application")
    applicant_name: str = Field(..., min_length=2, description="Full name of applicant")
    monthly_income: Optional[float] = Field(None, ge=0, description="Net monthly income (None if missing/to be extracted)")
    existing_emis: float = Field(default=0.0, ge=0, description="Total existing monthly EMI obligations")
    requested_amount: float = Field(..., gt=0, description="Principal loan amount requested")
    tenure_months: int = Field(..., gt=0, description="Loan tenure in months")
    annual_interest_rate: Optional[float] = Field(default=None, ge=0, description="Annual interest rate percentage")
    uploaded_document_path: Optional[str] = Field(default=None, description="Path to uploaded proof document")

    @field_validator("requested_amount")
    @classmethod
    def validate_requested_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Requested loan amount must be strictly greater than zero.")
        return round(v, 2)

    @field_validator("tenure_months")
    @classmethod
    def validate_tenure_months(cls, v: int) -> int:
        if v < 1 or v > 360:
            raise ValueError("Tenure months must be between 1 and 360.")
        return v


class DocumentExtractionResult(BaseModel):
    """Output from Document Agent."""
    applicant_name: Optional[str] = None
    monthly_income: Optional[float] = None
    existing_emis: Optional[float] = None
    requested_amount: Optional[float] = None
    tenure_months: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    missing_fields: List[str] = Field(default_factory=list)
    inconsistencies: List[str] = Field(default_factory=list)
    validation_passed: bool = True
    prompt_injection_detected: bool = False
    notes: str = ""


class EMICalculationResult(BaseModel):
    """Output from EMI Computation Agent."""
    principal: float
    annual_interest_rate: float
    tenure_months: int
    monthly_emi: float
    total_repayment: float
    total_interest: float
    is_zero_interest: bool = False
    calculation_formula: str = "P * r * (1+r)^n / ((1+r)^n - 1)"


class AffordabilityResult(BaseModel):
    """Output from Affordability Agent."""
    monthly_income: Optional[float] = None
    existing_emis: float
    proposed_emi: float
    total_debt: float
    foir: Optional[float] = None
    affordability_verdict: AffordabilityVerdictEnum
    max_allowed_debt: float
    available_capacity: float
    explanation: str


class CreditHistoryResult(BaseModel):
    """Output from Credit History Agent."""
    applicant_id: str
    record_found: bool = False
    missed_payments: int = 0
    defaults: int = 0
    fraud_flag: bool = False
    overdue_accounts: int = 0
    credit_score: Optional[int] = None
    credit_verdict: CreditVerdictEnum
    explanation: str


class CounterOfferResult(BaseModel):
    """Output from Counter-Offer Worker."""
    feasible: bool = False
    recommended_amount: Optional[float] = None
    recommended_tenure: Optional[int] = None
    recommended_emi: Optional[float] = None
    revised_foir: Optional[float] = None
    annual_interest_rate: Optional[float] = None
    original_amount: Optional[float] = None
    original_emi: Optional[float] = None
    original_tenure: Optional[int] = None
    tenure_extended: bool = False
    explanation: str = ""

    def __getitem__(self, item: str):
        return getattr(self, item)


class AgentStepAudit(BaseModel):
    """Audit log entry for an individual agent's execution."""
    agent_name: str
    status: str  # STARTED, COMPLETED, HALTED, FAILED, SKIPPED
    started_at: str
    completed_at: Optional[str] = None
    execution_time_ms: float = 0.0
    task_description: str
    output_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class FinalDecisionResponse(BaseModel):
    """Standardized final underwriting decision payload matching prompt section 8."""
    application_id: str
    decision: FinalDecisionEnum
    requested_amount: float
    emi: Optional[float] = None
    existing_emi: float
    monthly_income: Optional[float] = None
    foir: Optional[float] = None
    affordability: AffordabilityVerdictEnum
    credit_history: CreditVerdictEnum
    counter_offer: Optional[CounterOfferResult] = None
    reason: str
    justification_paragraph: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_audit_trail: List[AgentStepAudit] = Field(default_factory=list)


class SharedApplicantMemorySchema(BaseModel):
    """Common applicant shared memory record updated by all agents."""
    application_id: str
    applicant: Dict[str, Any] = Field(default_factory=dict)
    document_analysis: Dict[str, Any] = Field(default_factory=dict)
    emi_calculation: Dict[str, Any] = Field(default_factory=dict)
    affordability_analysis: Dict[str, Any] = Field(default_factory=dict)
    credit_analysis: Dict[str, Any] = Field(default_factory=dict)
    counter_offer: Optional[Dict[str, Any]] = None
    final_decision: Dict[str, Any] = Field(default_factory=dict)
    agent_audit_trail: List[AgentStepAudit] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

import pytest
from core.schemas import LoanApplicationInput
from core.policies import FinalDecisionEnum, AffordabilityVerdictEnum, CreditVerdictEnum
from core.shared_memory import SharedApplicantMemory, SilentOverwriteError
from agents.underwriting_manager import UnderwritingManager
from core.database import SessionLocal, get_application, init_db

# Ensure test DB is initialized
init_db()


@pytest.mark.asyncio
async def test_case_1_eligible_applicant_sanction():
    """Demonstration Case 1: Rahul Sharma — Verified income, low FOIR (31.87%), clean bureau -> SANCTION."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_APP001",
        applicant_name="Rahul Sharma",
        monthly_income=60000.0,
        existing_emis=8000.0,
        requested_amount=500000.0,
        tenure_months=60,
        annual_interest_rate=12.0
    )

    result = await manager.process_application(app, persist_db=True)

    assert result.decision == FinalDecisionEnum.SANCTION
    assert result.emi == 11122.22
    assert result.foir == 31.87
    assert result.affordability == AffordabilityVerdictEnum.PASS
    assert result.credit_history == CreditVerdictEnum.PASS
    assert result.counter_offer is None
    assert "within the configured affordability limit" in result.reason.lower()


@pytest.mark.asyncio
async def test_case_2_high_emi_burden_decline_with_counter_offer():
    """Demonstration Case 2: Priya Patel — High debt burden fails 40% FOIR ceiling -> DECLINE with Counter-Offer."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_APP002",
        applicant_name="Priya Patel",
        monthly_income=75000.0,
        existing_emis=24000.0,
        requested_amount=700000.0,
        tenure_months=36,
        annual_interest_rate=12.0
    )

    result = await manager.process_application(app, persist_db=True)

    assert result.decision == FinalDecisionEnum.DECLINE
    assert result.affordability == AffordabilityVerdictEnum.FAIL
    assert result.counter_offer is not None
    assert result.counter_offer.feasible is True
    assert result.counter_offer.revised_foir <= 40.0


@pytest.mark.asyncio
async def test_case_5_affordability_failure_counter_offer():
    """Demonstration Case 5: Sneha Rao — Affordability failure generates viable counter-offer."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_APP005",
        applicant_name="Sneha Rao",
        monthly_income=50000.0,
        existing_emis=12000.0,
        requested_amount=600000.0,
        tenure_months=48,
        annual_interest_rate=12.0
    )

    result = await manager.process_application(app, persist_db=True)

    assert result.decision == FinalDecisionEnum.DECLINE
    assert result.affordability == AffordabilityVerdictEnum.FAIL
    assert result.counter_offer is not None
    assert result.counter_offer.feasible is True
    assert result.counter_offer.recommended_amount <= 600000.0
    assert result.counter_offer.revised_foir <= 40.0


@pytest.mark.asyncio
async def test_case_3_missing_income_immediate_refer():
    """Demonstration Case 3: Amit Kumar — Missing income immediately halts pipeline -> REFER."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_APP003",
        applicant_name="Amit Kumar",
        monthly_income=None,  # Missing income
        existing_emis=5000.0,
        requested_amount=300000.0,
        tenure_months=48,
        annual_interest_rate=11.5
    )

    result = await manager.process_application(app, persist_db=True)

    assert result.decision == FinalDecisionEnum.REFER
    assert result.emi is None
    assert result.foir is None
    assert result.affordability == AffordabilityVerdictEnum.REFER
    assert "missing or unverified" in result.reason.lower()


@pytest.mark.asyncio
async def test_case_4_credit_default_hard_decline():
    """Demonstration Case 4: Vikram Singh — Verified bureau default -> hard DECLINE."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_APP004",
        applicant_name="Vikram Singh",
        monthly_income=90000.0,
        existing_emis=10000.0,
        requested_amount=400000.0,
        tenure_months=36,
        annual_interest_rate=12.0
    )

    result = await manager.process_application(app, persist_db=True)

    assert result.decision == FinalDecisionEnum.DECLINE
    assert result.credit_history == CreditVerdictEnum.DECLINE
    assert "default" in result.reason.lower()


@pytest.mark.asyncio
async def test_duplicate_application_detection():
    """Test 10: Duplicate application check in database."""
    manager = UnderwritingManager()
    app = LoanApplicationInput(
        application_id="TEST_DUP_001",
        applicant_name="Duplicate Applicant",
        monthly_income=50000.0,
        existing_emis=2000.0,
        requested_amount=100000.0,
        tenure_months=12,
        annual_interest_rate=10.0
    )

    # First run succeeds
    await manager.process_application(app, persist_db=True)

    db = SessionLocal()
    existing = get_application(db, "TEST_DUP_001")
    assert existing is not None
    assert existing.applicant_name == "Duplicate Applicant"
    db.close()


def test_shared_memory_silent_overwrite_protection():
    """Verify shared applicant memory raises SilentOverwriteError on unauthorized overwrite."""
    memory = SharedApplicantMemory("TEST_MEM_01")
    memory.update_section("document_analysis", {"income": 50000.0})

    with pytest.raises(SilentOverwriteError):
        # Attempt silent overwrite without allow_overwrite=True
        memory.update_section("document_analysis", {"income": 99999.0}, allow_overwrite=False)

    # With explicit allow_overwrite=True, it succeeds
    memory.update_section("document_analysis", {"income": 99999.0}, allow_overwrite=True)
    assert memory.get_section("document_analysis")["income"] == 99999.0

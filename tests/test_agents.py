import pytest
from core.shared_memory import SharedApplicantMemory
from core.policies import CreditVerdictEnum
from agents.document_agent import DocumentAgent
from agents.credit_history_agent import CreditHistoryAgent
from agents.counter_offer_agent import CounterOfferAgent
from tools.sample_pdf_generator import generate_sample_application_pdf


@pytest.mark.asyncio
async def test_credit_history_agent_clean_pass():
    """Test CreditHistoryAgent with verified clean record (APP001)."""
    memory = SharedApplicantMemory("APP001", {"applicant_name": "Rahul Sharma"})
    agent = CreditHistoryAgent()
    result = await agent.run(memory)

    assert result["credit_verdict"] == CreditVerdictEnum.PASS.value
    assert result["record_found"] is True
    assert result["defaults"] == 0
    assert result["fraud_flag"] is False


@pytest.mark.asyncio
async def test_credit_history_agent_unknown_refer():
    """Test 6: Unknown credit history returns UNKNOWN and refers for manual review."""
    memory = SharedApplicantMemory("APP_UNKNOWN_888", {"applicant_name": "Ghost Applicant"})
    agent = CreditHistoryAgent()
    result = await agent.run(memory)

    assert result["credit_verdict"] == CreditVerdictEnum.UNKNOWN.value
    assert result["record_found"] is False
    assert "UNKNOWN" in result["explanation"]


@pytest.mark.asyncio
async def test_credit_history_agent_fraud_flag_decline():
    """Test 7: Verified fraud flag triggers DECLINE."""
    memory = SharedApplicantMemory("APP006", {"applicant_name": "Deepak Verma"})
    agent = CreditHistoryAgent()
    result = await agent.run(memory)

    assert result["credit_verdict"] == CreditVerdictEnum.DECLINE.value
    assert result["fraud_flag"] is True
    assert "fraud indicator" in result["explanation"].lower()


@pytest.mark.asyncio
async def test_credit_history_agent_default_decline():
    """Test CreditHistoryAgent with historical loan default (APP004)."""
    memory = SharedApplicantMemory("APP004", {"applicant_name": "Vikram Singh"})
    agent = CreditHistoryAgent()
    result = await agent.run(memory)

    assert result["credit_verdict"] == CreditVerdictEnum.DECLINE.value
    assert result["defaults"] > 0


@pytest.mark.asyncio
async def test_counter_offer_generation():
    """Test 8: Counter-offer worker generates valid restructuring with FOIR <= 40%."""
    memory = SharedApplicantMemory("APP005", {})
    # Populate memory state simulating affordability failure
    memory.update_section("document_analysis", {
        "monthly_income": 50000.0,
        "existing_emis": 12000.0,
        "requested_amount": 600000.0,
        "tenure_months": 48,
        "annual_interest_rate": 12.0
    })
    memory.update_section("emi_calculation", {
        "monthly_emi": 15800.30
    })
    memory.update_section("affordability_analysis", {
        "foir": 55.6,
        "affordability_verdict": "FAIL"
    })

    agent = CounterOfferAgent()
    result = await agent.run(memory)

    assert result["feasible"] is True
    assert result["recommended_amount"] is not None
    assert result["recommended_amount"] <= 600000.0
    assert result["revised_foir"] <= 40.0
    assert result["recommended_emi"] is not None
    assert (result["recommended_emi"] + 12000.0) <= 20000.0  # 40% of 50k is 20k


@pytest.mark.asyncio
async def test_document_agent_prompt_injection_neutralization(tmp_path):
    """Test DocumentAgent detects and sanitizes adversarial prompt injection in uploaded PDF."""
    pdf_path = tmp_path / "adversarial_doc.pdf"
    generate_sample_application_pdf(
        file_path=str(pdf_path),
        applicant_name="Eve Hacker",
        monthly_income=80000.0,
        existing_emis=5000.0,
        requested_amount=300000.0,
        tenure_months=36,
        include_prompt_injection=True
    )

    memory = SharedApplicantMemory("APP_INJECT", {
        "applicant_name": "Eve Hacker",
        "uploaded_document_path": str(pdf_path)
    })

    agent = DocumentAgent()
    result = await agent.run(memory)

    assert result["prompt_injection_detected"] is True
    assert "PROMPT INJECTION DETECTED" in result["notes"]

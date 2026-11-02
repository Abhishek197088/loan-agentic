import pytest
from tools.affordability_calculator import evaluate_affordability
from core.policies import AffordabilityVerdictEnum


def test_normal_application_good_affordability():
    """Test 1: FOIR <= 40% passes affordability."""
    # Income 60,000; Existing 8,000; Proposed 11,122.22 -> Total 19,122.22 -> FOIR 31.87%
    result = evaluate_affordability(
        monthly_income=60000.0,
        existing_emis=8000.0,
        proposed_emi=11122.22,
        max_foir_percent=40.0
    )

    assert result.affordability_verdict == AffordabilityVerdictEnum.PASS
    assert result.foir == 31.87
    assert result.max_allowed_debt == 24000.0
    assert result.available_capacity == 16000.0


def test_application_exceeding_40_foir():
    """Test 2: FOIR > 40% fails affordability."""
    # Income 50,000; Existing 12,000; Proposed 15,800 -> Total 27,800 -> FOIR 55.6%
    result = evaluate_affordability(
        monthly_income=50000.0,
        existing_emis=12000.0,
        proposed_emi=15800.0,
        max_foir_percent=40.0
    )

    assert result.affordability_verdict == AffordabilityVerdictEnum.FAIL
    assert result.foir == 55.60
    assert result.max_allowed_debt == 20000.0
    assert result.available_capacity == 8000.0


def test_missing_monthly_income():
    """Test 3: Missing income returns REFER immediately without estimating or assuming."""
    result = evaluate_affordability(
        monthly_income=None,
        existing_emis=5000.0,
        proposed_emi=10000.0,
        max_foir_percent=40.0
    )

    assert result.affordability_verdict == AffordabilityVerdictEnum.REFER
    assert result.foir is None
    assert "missing or unverified" in result.explanation.lower()


def test_existing_emi_exceeding_income_capacity():
    """Test 5: Existing EMI alone exceeding 40% threshold fails affordability."""
    # Income 60,000; Max 40% = 24,000. Existing EMIs = 25,000
    result = evaluate_affordability(
        monthly_income=60000.0,
        existing_emis=25000.0,
        proposed_emi=5000.0,
        max_foir_percent=40.0
    )

    assert result.affordability_verdict == AffordabilityVerdictEnum.FAIL
    assert result.available_capacity == 0.0
    assert result.foir == 50.0
    assert "already consume or exceed" in result.explanation.lower()

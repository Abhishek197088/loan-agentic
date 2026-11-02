import pytest
from tools.emi_calculator import compute_emi, compute_max_affordable_principal


def test_standard_reducing_balance_emi():
    """Test 1: Deterministic reducing-balance EMI calculation (P=500k, r=12%, n=60m)."""
    result = compute_emi(principal=500000.0, annual_interest_rate=12.0, tenure_months=60)

    # Expected EMI is 11,122.22
    assert result.monthly_emi == 11122.22
    assert result.total_repayment == 667333.20
    assert result.total_interest == 167333.20
    assert result.is_zero_interest is False


def test_zero_interest_loan():
    """Test 4: Zero-interest loan calculation."""
    result = compute_emi(principal=240000.0, annual_interest_rate=0.0, tenure_months=24)

    assert result.monthly_emi == 10000.0
    assert result.total_interest == 0.0
    assert result.total_repayment == 240000.0
    assert result.is_zero_interest is True


def test_max_affordable_principal():
    """Test 9: Inverse EMI calculation to determine maximum affordable loan amount."""
    available_capacity = 11122.22
    rate = 12.0
    tenure = 60

    max_p = compute_max_affordable_principal(available_capacity, rate, tenure)
    # Inverting 11122.22 at 12% over 60m should yield ~500,000
    assert abs(max_p - 500000.0) < 50.0


def test_invalid_loan_amount():
    """Test 11: Validation failure on non-positive loan amount."""
    with pytest.raises(ValueError, match="strictly positive"):
        compute_emi(principal=0.0, annual_interest_rate=10.0, tenure_months=12)

    with pytest.raises(ValueError, match="strictly positive"):
        compute_emi(principal=-50000.0, annual_interest_rate=10.0, tenure_months=12)


def test_invalid_tenure():
    """Test 12: Validation failure on non-positive loan tenure."""
    with pytest.raises(ValueError, match="strictly positive"):
        compute_emi(principal=100000.0, annual_interest_rate=10.0, tenure_months=0)

    with pytest.raises(ValueError, match="strictly positive"):
        compute_emi(principal=100000.0, annual_interest_rate=10.0, tenure_months=-24)

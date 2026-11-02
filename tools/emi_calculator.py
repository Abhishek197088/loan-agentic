import math
from typing import Dict, Any
from core.schemas import EMICalculationResult


def compute_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int
) -> EMICalculationResult:
    """
    Deterministic reducing-balance EMI calculator.
    Formula:
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where:
        P = Principal loan amount
        r = Monthly interest rate (annual_rate / 12 / 100)
        n = Number of monthly installments

    Zero-interest loan:
        EMI = P / n
    """
    if principal <= 0:
        raise ValueError("Principal loan amount must be strictly positive.")
    if tenure_months <= 0:
        raise ValueError("Loan tenure in months must be strictly positive.")
    if annual_interest_rate < 0:
        raise ValueError("Annual interest rate cannot be negative.")

    # Zero-interest handling
    if annual_interest_rate == 0.0:
        emi = round(principal / tenure_months, 2)
        total_repayment = round(principal, 2)
        total_interest = 0.0
        return EMICalculationResult(
            principal=round(principal, 2),
            annual_interest_rate=0.0,
            tenure_months=tenure_months,
            monthly_emi=emi,
            total_repayment=total_repayment,
            total_interest=total_interest,
            is_zero_interest=True,
            calculation_formula="P / n (Zero Interest)"
        )

    # Monthly interest rate
    monthly_rate = annual_interest_rate / 12.0 / 100.0

    # Compounding factor: (1 + r)^n
    compound_factor = math.pow(1.0 + monthly_rate, tenure_months)

    # EMI calculation
    emi_raw = (principal * monthly_rate * compound_factor) / (compound_factor - 1.0)
    monthly_emi = round(emi_raw, 2)
    total_repayment = round(monthly_emi * tenure_months, 2)
    total_interest = round(total_repayment - principal, 2)

    return EMICalculationResult(
        principal=round(principal, 2),
        annual_interest_rate=annual_interest_rate,
        tenure_months=tenure_months,
        monthly_emi=monthly_emi,
        total_repayment=total_repayment,
        total_interest=total_interest,
        is_zero_interest=False,
        calculation_formula="P * r * (1+r)^n / ((1+r)^n - 1)"
    )


def compute_max_affordable_principal(
    available_monthly_emi: float,
    annual_interest_rate: float,
    tenure_months: int
) -> float:
    """
    Invert the reducing-balance EMI formula to determine the maximum affordable principal.
    Formula:
        P = EMI * ((1+r)^n - 1) / (r * (1+r)^n)
    """
    if available_monthly_emi <= 0 or tenure_months <= 0:
        return 0.0

    if annual_interest_rate == 0.0:
        return round(available_monthly_emi * tenure_months, 2)

    monthly_rate = annual_interest_rate / 12.0 / 100.0
    compound_factor = math.pow(1.0 + monthly_rate, tenure_months)
    principal_raw = available_monthly_emi * (compound_factor - 1.0) / (monthly_rate * compound_factor)

    return max(0.0, round(principal_raw, 2))

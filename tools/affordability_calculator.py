from typing import Optional
from core.schemas import AffordabilityResult
from core.policies import AffordabilityVerdictEnum


def evaluate_affordability(
    monthly_income: Optional[float],
    existing_emis: float,
    proposed_emi: float,
    max_foir_percent: float = 40.0
) -> AffordabilityResult:
    """
    Evaluates debt serviceability and Fixed Obligation to Income Ratio (FOIR).
    Policy:
        Total monthly EMI obligations must not exceed configured max_foir_percent (default 40%) of net monthly income.
    """
    existing_emis = max(0.0, round(existing_emis, 2))
    proposed_emi = max(0.0, round(proposed_emi, 2))
    total_debt = round(existing_emis + proposed_emi, 2)

    # Missing income rule: immediately REFER
    if monthly_income is None:
        return AffordabilityResult(
            monthly_income=None,
            existing_emis=existing_emis,
            proposed_emi=proposed_emi,
            total_debt=total_debt,
            foir=None,
            affordability_verdict=AffordabilityVerdictEnum.REFER,
            max_allowed_debt=0.0,
            available_capacity=0.0,
            explanation="Net monthly income is missing or unverified. Immediate referral for income verification required."
        )

    if monthly_income <= 0:
        return AffordabilityResult(
            monthly_income=monthly_income,
            existing_emis=existing_emis,
            proposed_emi=proposed_emi,
            total_debt=total_debt,
            foir=None,
            affordability_verdict=AffordabilityVerdictEnum.REFER,
            max_allowed_debt=0.0,
            available_capacity=0.0,
            explanation="Reported net monthly income is zero or negative. Referral required for financial audit."
        )

    max_allowed_debt = round(monthly_income * (max_foir_percent / 100.0), 2)
    available_capacity = max(0.0, round(max_allowed_debt - existing_emis, 2))
    foir = round((total_debt / monthly_income) * 100.0, 2)

    if existing_emis > max_allowed_debt:
        verdict = AffordabilityVerdictEnum.FAIL
        explanation = (
            f"Existing monthly debt obligations (₹{existing_emis:,.2f}) already consume or exceed "
            f"the maximum allowable {max_foir_percent}% debt threshold (₹{max_allowed_debt:,.2f}). "
            f"No additional debt capacity is available."
        )
    elif foir <= max_foir_percent:
        verdict = AffordabilityVerdictEnum.PASS
        explanation = (
            f"Applicant obligations satisfy affordability criteria. Total monthly debt "
            f"(₹{total_debt:,.2f}) accounts for {foir:.2f}% of net monthly income (₹{monthly_income:,.2f}), "
            f"below the maximum limit of {max_foir_percent}%."
        )
    else:
        verdict = AffordabilityVerdictEnum.FAIL
        explanation = (
            f"Proposed debt obligations (₹{total_debt:,.2f}) result in a FOIR of {foir:.2f}%, "
            f"which exceeds the institutional affordability threshold of {max_foir_percent}%. "
            f"Exceeds ceiling by ₹{round(total_debt - max_allowed_debt, 2):,.2f}."
        )

    return AffordabilityResult(
        monthly_income=round(monthly_income, 2),
        existing_emis=existing_emis,
        proposed_emi=proposed_emi,
        total_debt=total_debt,
        foir=foir,
        affordability_verdict=verdict,
        max_allowed_debt=max_allowed_debt,
        available_capacity=available_capacity,
        explanation=explanation
    )

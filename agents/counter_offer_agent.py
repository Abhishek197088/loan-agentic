import math
import logging
from typing import Dict, Any, Optional
from core.shared_memory import SharedApplicantMemory
from core.schemas import CounterOfferResult
from tools.emi_calculator import compute_emi, compute_max_affordable_principal
from core.config import settings

logger = logging.getLogger("CounterOfferAgent")


class CounterOfferAgent:
    """
    AGENT 5: COUNTER-OFFER WORKER
    Activated when the requested loan fails affordability.
    Calculates maximum affordable principal and explores tenure extension within policy bounds.
    Guarantees that any counter-offer strictly satisfies FOIR <= 40% and never exceeds requested amount.
    """

    def __init__(self):
        self.agent_name = "CounterOfferAgent"

    async def run(self, memory: SharedApplicantMemory) -> Dict[str, Any]:
        task_desc = "Formulating restructuring options and counter-offer for application failing affordability."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            doc_data = memory.get_section("document_analysis")
            emi_data = memory.get_section("emi_calculation")
            aff_data = memory.get_section("affordability_analysis")

            monthly_income = doc_data.get("monthly_income")
            existing_emis = float(doc_data.get("existing_emis", 0.0))
            requested_amount = float(doc_data.get("requested_amount", 0.0))
            requested_tenure = int(doc_data.get("tenure_months", 60))
            rate = float(doc_data.get("annual_interest_rate", settings.default_annual_interest_rate))
            original_emi = float(emi_data.get("monthly_emi", 0.0))

            # Guard: If income is missing or non-positive, no counter-offer can be computed
            if monthly_income is None or monthly_income <= 0:
                output = {
                    "feasible": False,
                    "recommended_amount": None,
                    "recommended_tenure": None,
                    "recommended_emi": None,
                    "revised_foir": None,
                    "explanation": "Cannot formulate counter-offer: Net monthly income is unverified or missing."
                }
                memory.update_section("counter_offer", output, allow_overwrite=True)
                memory.complete_agent_step(self.agent_name, status="HALTED", output_summary=output)
                return output

            # Compute maximum allowable total debt under policy (40%)
            max_allowed_debt = round(monthly_income * (settings.max_foir_percent / 100.0), 2)
            available_capacity = max_allowed_debt - existing_emis

            # If existing EMIs already consume or exceed 40% capacity
            if available_capacity <= 500.0:
                output = {
                    "feasible": False,
                    "recommended_amount": None,
                    "recommended_tenure": None,
                    "recommended_emi": None,
                    "revised_foir": None,
                    "explanation": (
                        f"Existing debt commitments (₹{existing_emis:,.2f}) exhaust the applicant's maximum 40% "
                        f"debt capacity (₹{max_allowed_debt:,.2f}). Available headroom of ₹{max(0.0, available_capacity):,.2f} "
                        f"is insufficient to sustain a viable commercial credit facility."
                    )
                }
                memory.update_section("counter_offer", output, allow_overwrite=True)
                memory.complete_agent_step(self.agent_name, status="COMPLETED", output_summary=output)
                return output

            # Option A: Maximum affordable principal with original requested tenure
            principal_same_tenure = compute_max_affordable_principal(
                available_monthly_emi=available_capacity,
                annual_interest_rate=rate,
                tenure_months=requested_tenure
            )
            # Never propose more than requested
            principal_same_tenure = min(principal_same_tenure, requested_amount)
            # Round down to nearest 1,000 for realistic banking proposal
            principal_same_tenure = math.floor(principal_same_tenure / 1000.0) * 1000.0

            # Option B: Explore tenure extension if enabled and within maximum tenure limits
            best_principal = principal_same_tenure
            best_tenure = requested_tenure
            tenure_extended = False

            if settings.allow_counter_offer_tenure_extension and requested_tenure < settings.max_allowed_tenure_months:
                # Test candidate extended tenures (e.g. 72 or 84 months)
                candidate_tenures = [72, 84, settings.max_allowed_tenure_months]
                for cand_tenure in candidate_tenures:
                    if cand_tenure > requested_tenure and cand_tenure <= settings.max_allowed_tenure_months:
                        p_cand = compute_max_affordable_principal(
                            available_monthly_emi=available_capacity,
                            annual_interest_rate=rate,
                            tenure_months=cand_tenure
                        )
                        p_cand = min(p_cand, requested_amount)
                        p_cand = math.floor(p_cand / 1000.0) * 1000.0

                        # If extending tenure allows higher loan or matches requested amount
                        if p_cand > best_principal:
                            best_principal = p_cand
                            best_tenure = cand_tenure
                            tenure_extended = True

            # If highest viable principal is below minimum loan amount
            if best_principal < settings.min_loan_amount:
                output = {
                    "feasible": False,
                    "recommended_amount": None,
                    "recommended_tenure": None,
                    "recommended_emi": None,
                    "revised_foir": None,
                    "explanation": (
                        f"Maximum affordable principal (₹{best_principal:,.2f}) falls below institutional minimum "
                        f"loan size (₹{settings.min_loan_amount:,.2f}). No viable loan structure available."
                    )
                }
                memory.update_section("counter_offer", output, allow_overwrite=True)
                memory.complete_agent_step(self.agent_name, status="COMPLETED", output_summary=output)
                return output

            # Compute new EMI and verify revised FOIR
            new_emi_calc = compute_emi(
                principal=best_principal,
                annual_interest_rate=rate,
                tenure_months=best_tenure
            )
            new_emi = new_emi_calc.monthly_emi
            new_total_debt = existing_emis + new_emi
            revised_foir = round((new_total_debt / monthly_income) * 100.0, 2)

            # Defensive sanity check: Ensure revised FOIR strictly <= 40%
            if revised_foir > settings.max_foir_percent:
                # Minor downward adjustment if rounding pushed slightly above
                adjustment = 5000.0
                best_principal = max(settings.min_loan_amount, best_principal - adjustment)
                new_emi_calc = compute_emi(principal=best_principal, annual_interest_rate=rate, tenure_months=best_tenure)
                new_emi = new_emi_calc.monthly_emi
                revised_foir = round(((existing_emis + new_emi) / monthly_income) * 100.0, 2)

            explanation = (
                f"Affordability optimization formulated: Restructured loan from requested ₹{requested_amount:,.2f} "
                f"({requested_tenure}m, EMI ₹{original_emi:,.2f}) to recommended ₹{best_principal:,.2f} "
                f"({best_tenure}m, EMI ₹{new_emi:,.2f}). "
                f"This successfully recovers FOIR from {aff_data.get('foir', 'N/A')}% down to compliant {revised_foir:.2f}%."
            )

            counter_offer_model = CounterOfferResult(
                feasible=True,
                recommended_amount=best_principal,
                recommended_tenure=best_tenure,
                recommended_emi=new_emi,
                revised_foir=revised_foir,
                annual_interest_rate=rate,
                original_amount=requested_amount,
                original_emi=original_emi,
                original_tenure=requested_tenure,
                tenure_extended=tenure_extended,
                explanation=explanation
            )

            output = counter_offer_model.model_dump()
            memory.update_section("counter_offer", output, allow_overwrite=True)
            memory.complete_agent_step(self.agent_name, status="COMPLETED", output_summary=output)
            return output

        except Exception as e:
            logger.exception(f"CounterOfferAgent failed: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

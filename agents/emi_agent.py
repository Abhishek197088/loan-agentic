import logging
from typing import Dict, Any
from core.shared_memory import SharedApplicantMemory
from tools.emi_calculator import compute_emi
from core.config import settings

logger = logging.getLogger("EMIAgent")


class EMIAgent:
    """
    AGENT 2: EMI COMPUTATION AGENT
    Deterministically computes loan EMI, total repayment, and total interest
    using the reducing-balance formula. Never delegates math to the LLM.
    """

    def __init__(self):
        self.agent_name = "EMIAgent"

    async def run(self, memory: SharedApplicantMemory) -> Dict[str, Any]:
        task_desc = "Deterministically computing proposed EMI, total repayment, and total interest using reducing-balance formula."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            doc_data = memory.get_section("document_analysis")
            principal = doc_data.get("requested_amount")
            tenure = doc_data.get("tenure_months")
            rate = doc_data.get("annual_interest_rate", settings.default_annual_interest_rate)

            if principal is None or tenure is None:
                raise ValueError("Cannot calculate EMI: Requested loan amount or tenure is missing.")

            principal = float(principal)
            tenure = int(tenure)
            rate = float(rate)

            # Deterministic calculation via Python tool
            emi_result = compute_emi(
                principal=principal,
                annual_interest_rate=rate,
                tenure_months=tenure
            )

            output = emi_result.model_dump()
            memory.update_section("emi_calculation", output, allow_overwrite=True)
            memory.complete_agent_step(self.agent_name, status="COMPLETED", output_summary=output)
            return output

        except Exception as e:
            logger.exception(f"EMIAgent failed: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

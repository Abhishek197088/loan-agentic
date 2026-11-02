import logging
from typing import Dict, Any
from core.shared_memory import SharedApplicantMemory
from tools.affordability_calculator import evaluate_affordability
from core.config import settings

logger = logging.getLogger("AffordabilityAgent")


class AffordabilityAgent:
    """
    AGENT 3: AFFORDABILITY AGENT
    Evaluates debt obligations, debt service coverage, and FOIR against
    institutional policy (FOIR <= 40%). Computes available borrowing headroom.
    """

    def __init__(self):
        self.agent_name = "AffordabilityAgent"

    async def run(self, memory: SharedApplicantMemory) -> Dict[str, Any]:
        task_desc = f"Evaluating applicant affordability and FOIR against institutional {settings.max_foir_percent}% ceiling."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            doc_data = memory.get_section("document_analysis")
            emi_data = memory.get_section("emi_calculation")

            monthly_income = doc_data.get("monthly_income")
            existing_emis = float(doc_data.get("existing_emis", 0.0))
            proposed_emi = float(emi_data.get("monthly_emi", 0.0))

            affordability_result = evaluate_affordability(
                monthly_income=monthly_income,
                existing_emis=existing_emis,
                proposed_emi=proposed_emi,
                max_foir_percent=settings.max_foir_percent
            )

            output = affordability_result.model_dump()
            output["affordability_verdict"] = affordability_result.affordability_verdict.value
            memory.update_section("affordability_analysis", output, allow_overwrite=True)

            status = "COMPLETED" if affordability_result.affordability_verdict.value == "PASS" else "FLAGGED"
            memory.complete_agent_step(self.agent_name, status=status, output_summary=output)
            return output

        except Exception as e:
            logger.exception(f"AffordabilityAgent failed: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

import json
import logging
from typing import Dict, Any, Optional
from core.shared_memory import SharedApplicantMemory
from core.policies import CreditVerdictEnum
from core.config import settings

logger = logging.getLogger("CreditHistoryAgent")


class CreditHistoryAgent:
    """
    AGENT 4: CREDIT-HISTORY AGENT
    Queries historical credit bureau records for delinquency, default, and fraud indicators.
    Strictly applies bureau risk policies:
    - Fraud or Defaults -> DECLINE
    - Missed payments or Overdue -> REFER
    - Clean -> PASS
    - Missing record -> UNKNOWN (REFER)
    """

    def __init__(self):
        self.agent_name = "CreditHistoryAgent"
        self._db_path = settings.credit_history_path

    def _load_credit_database(self) -> Dict[str, Any]:
        if not self._db_path.exists():
            return {"records": []}
        try:
            with open(self._db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read credit database from {self._db_path}: {e}")
            return {"records": []}

    async def run(self, memory: SharedApplicantMemory) -> Dict[str, Any]:
        task_desc = "Querying historical credit database for defaults, fraud indicators, and payment delinquencies."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            applicant_id = memory.application_id
            doc_data = memory.get_section("document_analysis")
            applicant_name = (
                doc_data.get("applicant_name")
                or memory.get_applicant_field("applicant_name")
                or ""
            ).strip().lower()

            db_data = self._load_credit_database()
            records = db_data.get("records", [])

            # Match by applicant_id or applicant_name
            matched_record: Optional[Dict[str, Any]] = None
            for rec in records:
                if rec.get("applicant_id", "").strip().upper() == applicant_id.strip().upper():
                    matched_record = rec
                    break
                # Secondary matching by name
                if applicant_name and rec.get("applicant_name", "").strip().lower() == applicant_name:
                    matched_record = rec
                    break

            # Rule: No record must not automatically mean good credit -> return UNKNOWN (REFER)
            if not matched_record:
                output = {
                    "applicant_id": applicant_id,
                    "record_found": False,
                    "missed_payments": 0,
                    "defaults": 0,
                    "fraud_flag": False,
                    "overdue_accounts": 0,
                    "credit_score": None,
                    "credit_verdict": CreditVerdictEnum.UNKNOWN.value,
                    "explanation": "No bureau credit record found for applicant. Bureau history is UNKNOWN; manual bureau onboarding and verification required."
                }
                memory.update_section("credit_analysis", output, allow_overwrite=True)
                memory.complete_agent_step(self.agent_name, status="FLAGGED", output_summary=output)
                return output

            # Evaluate found record
            missed = int(matched_record.get("missed_payments", 0))
            defaults = int(matched_record.get("defaults", 0))
            fraud = bool(matched_record.get("fraud_flag", False))
            overdue = int(matched_record.get("overdue_accounts", 0))
            score = matched_record.get("credit_score")

            if fraud or defaults > 0:
                verdict = CreditVerdictEnum.DECLINE
                reasons = []
                if fraud:
                    reasons.append("verified fraud indicator flagged")
                if defaults > 0:
                    reasons.append(f"{defaults} previous loan default(s) confirmed")
                explanation = f"High credit risk identified: {', '.join(reasons)}. Rejection mandated by policy."
            elif missed > 0 or overdue > 0:
                verdict = CreditVerdictEnum.REFER
                explanation = (
                    f"Bureau record displays minor delinquencies: {missed} missed payment(s) and "
                    f"{overdue} overdue account(s). Referral to credit officer required."
                )
            else:
                verdict = CreditVerdictEnum.PASS
                explanation = (
                    f"Satisfactory bureau credit performance verified (Score: {score or 'Good'}). "
                    f"Zero missed payments, zero defaults, and zero fraud flags."
                )

            output = {
                "applicant_id": applicant_id,
                "record_found": True,
                "missed_payments": missed,
                "defaults": defaults,
                "fraud_flag": fraud,
                "overdue_accounts": overdue,
                "credit_score": score,
                "credit_verdict": verdict.value,
                "explanation": explanation
            }

            memory.update_section("credit_analysis", output, allow_overwrite=True)
            status = "COMPLETED" if verdict == CreditVerdictEnum.PASS else "FLAGGED"
            memory.complete_agent_step(self.agent_name, status=status, output_summary=output)
            return output

        except Exception as e:
            logger.exception(f"CreditHistoryAgent failed: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

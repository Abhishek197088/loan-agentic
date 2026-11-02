import os
import logging
from typing import Dict, Any, List, Optional
from core.shared_memory import SharedApplicantMemory
from core.schemas import DocumentExtractionResult
from tools.document_extractor import (
    extract_text_from_pdf,
    parse_financial_fields_from_text,
    reconcile_declared_vs_extracted
)
from core.config import settings

logger = logging.getLogger("DocumentAgent")


class DocumentAgent:
    """
    AGENT 1: DOCUMENT AGENT
    Extracts and validates financial attributes from submitted application and uploaded PDFs.
    Identifies missing fields and checks for prompt injection or data discrepancies.
    Never invents missing financial information.
    """

    def __init__(self):
        self.agent_name = "DocumentAgent"

    async def run(self, memory: SharedApplicantMemory) -> Dict[str, Any]:
        task_desc = "Extracting and validating applicant financial data from application inputs and documents."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            applicant_data = memory.get_section("applicant")
            doc_path = applicant_data.get("uploaded_document_path")

            extracted_from_doc: Optional[DocumentExtractionResult] = None
            inconsistencies: List[str] = []
            notes: List[str] = []

            # 1. Process uploaded PDF if provided
            if doc_path and os.path.exists(doc_path):
                try:
                    raw_text = extract_text_from_pdf(doc_path)
                    extracted_from_doc = parse_financial_fields_from_text(raw_text)
                    if extracted_from_doc.prompt_injection_detected:
                        notes.append("PROMPT INJECTION DETECTED: Sanitized and logged security alert.")

                    # Reconcile declared data against document data
                    inconsistencies = reconcile_declared_vs_extracted(applicant_data, extracted_from_doc)
                    if inconsistencies:
                        notes.append(f"Inconsistencies detected: {'; '.join(inconsistencies)}")
                except Exception as ex:
                    logger.error(f"Error extracting PDF: {ex}")
                    notes.append(f"PDF extraction error: {str(ex)}")

            # 2. Reconcile final applicant values
            # Prioritize verified document data where available, fallback to declared, but never invent.
            name = (
                applicant_data.get("applicant_name")
                or (extracted_from_doc.applicant_name if extracted_from_doc else None)
            )

            # Monthly income: MUST NEVER BE INVENTED
            income = applicant_data.get("monthly_income")
            if income is None and extracted_from_doc and extracted_from_doc.monthly_income is not None:
                income = extracted_from_doc.monthly_income

            # Existing EMIs
            existing_emis = applicant_data.get("existing_emis", 0.0)
            if (existing_emis == 0.0 or existing_emis is None) and extracted_from_doc and extracted_from_doc.existing_emis:
                existing_emis = extracted_from_doc.existing_emis

            # Requested amount
            amount = (
                applicant_data.get("requested_amount")
                or (extracted_from_doc.requested_amount if extracted_from_doc else None)
            )

            # Tenure
            tenure = (
                applicant_data.get("tenure_months")
                or (extracted_from_doc.tenure_months if extracted_from_doc else None)
            )

            # Interest rate
            rate = applicant_data.get("annual_interest_rate")
            if rate is None and extracted_from_doc and extracted_from_doc.annual_interest_rate:
                rate = extracted_from_doc.annual_interest_rate
            if rate is None:
                rate = settings.default_annual_interest_rate

            # 3. Catalog missing fields
            missing_fields: List[str] = []
            if not name:
                missing_fields.append("applicant_name")
            if income is None:
                missing_fields.append("monthly_income")
            if amount is None or amount <= 0:
                missing_fields.append("requested_amount")
            if tenure is None or tenure <= 0:
                missing_fields.append("tenure_months")

            validation_passed = (len(missing_fields) == 0) and (not (extracted_from_doc and extracted_from_doc.prompt_injection_detected))

            output = {
                "applicant_name": name,
                "monthly_income": income,
                "existing_emis": float(existing_emis or 0.0),
                "requested_amount": float(amount) if amount else None,
                "tenure_months": int(tenure) if tenure else None,
                "annual_interest_rate": float(rate),
                "missing_fields": missing_fields,
                "inconsistencies": inconsistencies,
                "validation_passed": validation_passed,
                "prompt_injection_detected": bool(extracted_from_doc and extracted_from_doc.prompt_injection_detected),
                "notes": " ".join(notes) if notes else "Document extraction and validation completed successfully."
            }

            memory.update_section("document_analysis", output, allow_overwrite=True)
            status = "COMPLETED" if validation_passed else ("HALTED" if "monthly_income" in missing_fields else "FLAGGED")
            memory.complete_agent_step(self.agent_name, status=status, output_summary=output)
            return output

        except Exception as e:
            logger.exception(f"DocumentAgent failed: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

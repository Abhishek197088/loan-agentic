import logging
from typing import Dict, Any, Optional
from core.shared_memory import SharedApplicantMemory
from core.schemas import LoanApplicationInput, FinalDecisionResponse, AgentStepAudit
from core.policies import FinalDecisionEnum, AffordabilityVerdictEnum, CreditVerdictEnum, UnderwritingPolicy
from core.database import SessionLocal, save_application_record
from agents.document_agent import DocumentAgent
from agents.emi_agent import EMIAgent
from agents.affordability_agent import AffordabilityAgent
from agents.credit_history_agent import CreditHistoryAgent
from agents.counter_offer_agent import CounterOfferAgent
from agents.kernel_service import kernel_service

logger = logging.getLogger("UnderwritingManager")


class UnderwritingManager:
    """
    AGENT 6: UNDERWRITING MANAGER
    Central orchestrator implementing Manager-Worker delegation architecture:
    1. Initializes shared memory.
    2. Delegates to DocumentAgent.
    3. Enforces strict dependency: If income missing, HALTS immediately and yields REFER.
    4. Delegates to EMIAgent and AffordabilityAgent.
    5. Delegates to CreditHistoryAgent.
    6. If affordability fails, invokes CounterOfferAgent.
    7. Resolves conflicting worker verdicts into final decision: SANCTION, DECLINE, or REFER.
    8. Synthesizes executive explanation and commits immutable audit trail to database.
    """

    def __init__(self):
        self.agent_name = "UnderwritingManager"
        self.doc_agent = DocumentAgent()
        self.emi_agent = EMIAgent()
        self.aff_agent = AffordabilityAgent()
        self.credit_agent = CreditHistoryAgent()
        self.counter_offer_agent = CounterOfferAgent()

    async def process_application(
        self,
        app_input: LoanApplicationInput,
        shared_memory: Optional[SharedApplicantMemory] = None,
        persist_db: bool = True
    ) -> FinalDecisionResponse:
        """Execute complete multi-agent workflow."""
        memory = shared_memory or SharedApplicantMemory(
            application_id=app_input.application_id,
            initial_applicant_data=app_input.model_dump()
        )

        task_desc = f"Orchestrating end-to-end multi-agent underwriting assessment for application {app_input.application_id}."
        memory.start_agent_step(self.agent_name, task_desc)

        try:
            # Step 1: Document Extraction and Validation
            doc_output = await self.doc_agent.run(memory)

            # Step 2: Critical Income Check - Immediate Halt on Missing Income
            monthly_income = doc_output.get("monthly_income")
            if monthly_income is None or monthly_income <= 0:
                decision = FinalDecisionEnum.REFER
                reason = UnderwritingPolicy.REASON_INCOME_MISSING
                justification = await kernel_service.generate_explanation(
                    applicant_name=doc_output.get("applicant_name") or app_input.applicant_name,
                    decision=decision.value,
                    requested_amount=app_input.requested_amount,
                    emi=None,
                    foir=None,
                    credit_verdict=CreditVerdictEnum.UNKNOWN.value,
                    counter_offer=None,
                    reason=reason
                )

                decision_dict = {
                    "application_id": app_input.application_id,
                    "decision": decision.value,
                    "requested_amount": app_input.requested_amount,
                    "emi": None,
                    "existing_emi": app_input.existing_emis,
                    "monthly_income": None,
                    "foir": None,
                    "affordability": AffordabilityVerdictEnum.REFER.value,
                    "credit_history": CreditVerdictEnum.UNKNOWN.value,
                    "counter_offer": None,
                    "reason": reason,
                    "justification_paragraph": justification
                }

                memory.update_section("final_decision", decision_dict, allow_overwrite=True)
                memory.complete_agent_step(self.agent_name, status="HALTED", output_summary=decision_dict)

                if persist_db:
                    self._persist_to_database(memory, decision_dict)

                return FinalDecisionResponse(
                    application_id=app_input.application_id,
                    decision=decision,
                    requested_amount=app_input.requested_amount,
                    emi=None,
                    existing_emi=app_input.existing_emis,
                    monthly_income=None,
                    foir=None,
                    affordability=AffordabilityVerdictEnum.REFER,
                    credit_history=CreditVerdictEnum.UNKNOWN,
                    counter_offer=None,
                    reason=reason,
                    justification_paragraph=justification,
                    agent_audit_trail=memory.get_audit_trail()
                )

            # Step 3: Deterministic EMI Calculation
            emi_output = await self.emi_agent.run(memory)
            calculated_emi = emi_output.get("monthly_emi")

            # Step 4: Affordability & FOIR Evaluation
            aff_output = await self.aff_agent.run(memory)
            aff_verdict = aff_output.get("affordability_verdict")
            foir_val = aff_output.get("foir")

            # Step 5: Bureau Credit History Query
            credit_output = await self.credit_agent.run(memory)
            credit_verdict = credit_output.get("credit_verdict")

            # Step 6: Counter-Offer Formulation (Triggered if Affordability Fails)
            counter_offer_data = None
            if aff_verdict == AffordabilityVerdictEnum.FAIL.value:
                counter_offer_output = await self.counter_offer_agent.run(memory)
                if counter_offer_output.get("feasible"):
                    counter_offer_data = counter_offer_output

            # Step 7: Final Decision Synthesis & Policy Conflict Resolution
            decision, reason = self._resolve_decision_policy(
                doc_output=doc_output,
                aff_output=aff_output,
                credit_output=credit_output,
                counter_offer_data=counter_offer_data
            )

            # Step 8: Executive Justification Synthesis
            justification = await kernel_service.generate_explanation(
                applicant_name=doc_output.get("applicant_name") or app_input.applicant_name,
                decision=decision.value,
                requested_amount=app_input.requested_amount,
                emi=calculated_emi,
                foir=foir_val,
                credit_verdict=credit_verdict,
                counter_offer=counter_offer_data,
                reason=reason
            )

            decision_dict = {
                "application_id": app_input.application_id,
                "decision": decision.value,
                "requested_amount": app_input.requested_amount,
                "emi": calculated_emi,
                "existing_emi": app_input.existing_emis,
                "monthly_income": monthly_income,
                "foir": foir_val,
                "affordability": aff_verdict,
                "credit_history": credit_verdict,
                "counter_offer": counter_offer_data,
                "reason": reason,
                "justification_paragraph": justification
            }

            memory.update_section("final_decision", decision_dict, allow_overwrite=True)
            memory.complete_agent_step(self.agent_name, status="COMPLETED", output_summary=decision_dict)

            # Step 9: Atomic Database Persistence
            if persist_db:
                self._persist_to_database(memory, decision_dict)

            return FinalDecisionResponse(
                application_id=app_input.application_id,
                decision=decision,
                requested_amount=app_input.requested_amount,
                emi=calculated_emi,
                existing_emi=app_input.existing_emis,
                monthly_income=monthly_income,
                foir=foir_val,
                affordability=AffordabilityVerdictEnum(aff_verdict),
                credit_history=CreditVerdictEnum(credit_verdict),
                counter_offer=memory.get_section("counter_offer"),
                reason=reason,
                justification_paragraph=justification,
                agent_audit_trail=memory.get_audit_trail()
            )

        except Exception as e:
            logger.exception(f"UnderwritingManager failed during pipeline execution: {e}")
            memory.complete_agent_step(self.agent_name, status="FAILED", error_message=str(e))
            raise

    def _resolve_decision_policy(
        self,
        doc_output: Dict[str, Any],
        aff_output: Dict[str, Any],
        credit_output: Dict[str, Any],
        counter_offer_data: Optional[Dict[str, Any]]
    ) -> tuple[FinalDecisionEnum, str]:
        """
        Enforce comprehensive underwriting decision matrix:
        1. Hard Credit Rejections (Fraud, Defaults) -> DECLINE
        2. Unknown Credit or Delinquencies -> REFER
        3. Document discrepancies / Security alerts -> REFER
        4. Affordability:
           - If Credit is PASS and Affordability is PASS -> SANCTION
           - If Credit is PASS and Affordability is FAIL:
             DECLINE original request with counter-offer (or REFER if counter-offer feasible)
        """
        credit_verdict = credit_output.get("credit_verdict")
        aff_verdict = aff_output.get("affordability_verdict")
        inconsistencies = doc_output.get("inconsistencies", [])
        prompt_injection = doc_output.get("prompt_injection_detected", False)

        # 1. Hard Credit Rejection
        if credit_verdict == CreditVerdictEnum.DECLINE.value:
            if credit_output.get("fraud_flag"):
                return FinalDecisionEnum.DECLINE, UnderwritingPolicy.REASON_CREDIT_FRAUD
            return FinalDecisionEnum.DECLINE, UnderwritingPolicy.REASON_CREDIT_DEFAULT

        # 2. Credit Delinquency or Unknown Record
        if credit_verdict == CreditVerdictEnum.UNKNOWN.value:
            return FinalDecisionEnum.REFER, UnderwritingPolicy.REASON_CREDIT_UNKNOWN
        if credit_verdict == CreditVerdictEnum.REFER.value:
            return FinalDecisionEnum.REFER, UnderwritingPolicy.REASON_CREDIT_DELINQUENT

        # 3. Document or Security Discrepancies
        if prompt_injection:
            return FinalDecisionEnum.REFER, "Potential adversarial injection detected in submitted documentation. Referred for fraud security audit."
        if inconsistencies:
            return FinalDecisionEnum.REFER, f"Discrepancies identified between declared figures and documentation: {'; '.join(inconsistencies)}. Referred for manual document audit."

        # 4. Affordability Evaluation
        if aff_verdict == AffordabilityVerdictEnum.PASS.value and credit_verdict == CreditVerdictEnum.PASS.value:
            return FinalDecisionEnum.SANCTION, UnderwritingPolicy.REASON_SANCTION_APPROVED

        if aff_verdict == AffordabilityVerdictEnum.FAIL.value:
            if counter_offer_data and counter_offer_data.get("feasible"):
                return (
                    FinalDecisionEnum.DECLINE,
                    f"Requested terms exceed the 40% FOIR ceiling (FOIR: {aff_output.get('foir', 'N/A')}%). "
                    f"A structured counter-offer of ₹{counter_offer_data['recommended_amount']:,.2f} "
                    f"at {counter_offer_data['recommended_tenure']} months is available for consideration."
                )
            else:
                return (
                    FinalDecisionEnum.DECLINE,
                    f"Proposed debt obligations result in a non-viable FOIR of {aff_output.get('foir', 'N/A')}%. "
                    f"No feasible counter-offer structure is available within policy boundaries."
                )

        return FinalDecisionEnum.REFER, "Application requires manual exception review by senior credit committee."

    def _persist_to_database(self, memory: SharedApplicantMemory, decision_dict: Dict[str, Any]) -> None:
        """Persist application and audit log records to SQLite inside a transaction."""
        db = SessionLocal()
        try:
            doc_data = memory.get_section("document_analysis")
            save_application_record(
                db=db,
                app_id=decision_dict["application_id"],
                name=doc_data.get("applicant_name") or memory.get_applicant_field("applicant_name") or "Unknown",
                income=decision_dict.get("monthly_income"),
                existing_emis=float(decision_dict.get("existing_emi", 0.0)),
                amount=float(decision_dict["requested_amount"]),
                tenure=int(doc_data.get("tenure_months") or memory.get_applicant_field("tenure_months") or 60),
                rate=float(doc_data.get("annual_interest_rate") or memory.get_applicant_field("annual_interest_rate") or 12.0),
                emi=decision_dict.get("emi"),
                foir=decision_dict.get("foir"),
                affordability=decision_dict.get("affordability", "REFER"),
                credit=decision_dict.get("credit_history", "UNKNOWN"),
                decision=decision_dict["decision"],
                counter_offer=decision_dict.get("counter_offer"),
                reason=decision_dict["reason"],
                justification=decision_dict["justification_paragraph"],
                shared_memory_dict=memory.to_dict(),
                audit_trail=[step.model_dump() for step in memory.get_audit_trail()]
            )
        except Exception as e:
            logger.error(f"Failed to persist application to database: {e}")
            db.rollback()
        finally:
            db.close()

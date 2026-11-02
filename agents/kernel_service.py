import logging
from typing import Optional, Dict, Any
from core.config import settings

logger = logging.getLogger("KernelService")


class KernelService:
    """
    Microsoft Semantic Kernel integration layer.
    Manages Kernel lifecycle, OpenAI connectors, and rule-based fallback mode.
    """

    def __init__(self):
        self.kernel = None
        self.is_llm_enabled = False
        self._init_kernel()

    def _init_kernel(self):
        try:
            import semantic_kernel as sk
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

            self.kernel = sk.Kernel()

            # Check if valid OpenAI key configured
            api_key = settings.openai_api_key.strip()
            if api_key and not api_key.startswith("sk-placeholder") and len(api_key) > 10:
                chat_service = OpenAIChatCompletion(
                    service_id="underwriting-chat",
                    ai_model_id=settings.openai_model_name,
                    api_key=api_key,
                    base_url=settings.openai_base_url if settings.openai_base_url else None
                )
                self.kernel.add_service(chat_service)
                self.is_llm_enabled = True
                logger.info("Semantic Kernel initialized with OpenAI Chat Completion connector.")
            else:
                self.is_llm_enabled = False
                logger.info("Operating in deterministic Rule-Based Fallback Mode (No active OpenAI API key).")
        except Exception as e:
            logger.warning(f"Semantic Kernel initialization fallback: {e}")
            self.is_llm_enabled = False

    async def generate_explanation(
        self,
        applicant_name: str,
        decision: str,
        requested_amount: float,
        emi: Optional[float],
        foir: Optional[float],
        credit_verdict: str,
        counter_offer: Optional[Dict[str, Any]],
        reason: str
    ) -> str:
        """
        Generate a comprehensive, audit-ready one-paragraph executive justification.
        Uses Semantic Kernel if LLM is enabled, otherwise deterministic policy templates.
        """
        if self.is_llm_enabled and self.kernel:
            try:
                from semantic_kernel.contents import ChatHistory

                chat_service = self.kernel.get_service("underwriting-chat")
                history = ChatHistory()
                history.add_system_message(
                    "You are a Senior Loan Underwriting Risk Officer at a regulated financial institution. "
                    "Draft a concise, professional, single-paragraph executive credit justification for the credit committee. "
                    "Incorporate the official decision, applicant name, requested amount, EMI, FOIR, credit history verdict, "
                    "counter-offer (if any), and core regulatory rationale. Do not invent numbers. Be authoritative and concise."
                )

                prompt = (
                    f"Applicant: {applicant_name}\n"
                    f"Requested Amount: ₹{requested_amount:,.2f}\n"
                    f"Final Decision: {decision}\n"
                    f"Proposed EMI: ₹{emi:,.2f}" if emi else "Proposed EMI: N/A\n"
                    f"FOIR: {foir:.2f}%" if foir is not None else "FOIR: N/A\n"
                    f"Credit Bureau Status: {credit_verdict}\n"
                    f"Decision Reason: {reason}\n"
                    f"Counter Offer: {counter_offer}\n"
                )
                history.add_user_message(prompt)
                response = await chat_service.get_chat_message_content(chat_history=history)
                if response and response.content:
                    return str(response.content).strip()
            except Exception as ex:
                logger.warning(f"LLM generation failed, switching to rule-based fallback: {ex}")

        # Deterministic Rule-Based Fallback Synthesis
        return self._generate_fallback_justification(
            applicant_name=applicant_name,
            decision=decision,
            requested_amount=requested_amount,
            emi=emi,
            foir=foir,
            credit_verdict=credit_verdict,
            counter_offer=counter_offer,
            reason=reason
        )

    def _generate_fallback_justification(
        self,
        applicant_name: str,
        decision: str,
        requested_amount: float,
        emi: Optional[float],
        foir: Optional[float],
        credit_verdict: str,
        counter_offer: Optional[Dict[str, Any]],
        reason: str
    ) -> str:
        """Deterministic policy-compliant paragraph justification."""
        if decision == "SANCTION":
            return (
                f"Credit Underwriting Appraisal for {applicant_name} confirms complete compliance with institutional risk standards. "
                f"The requested principal of ₹{requested_amount:,.2f} at a calculated monthly EMI of ₹{emi:,.2f} results in a healthy "
                f"Fixed Obligation to Income Ratio (FOIR) of {foir:.2f}%, comfortably under the regulatory threshold of 40.0%. "
                f"Historical credit records reflect satisfactory bureau performance ({credit_verdict}) with zero defaults or adverse flags. "
                f"The loan application is formally approved for sanction."
            )
        elif decision == "DECLINE":
            co_text = ""
            if counter_offer and counter_offer.get("feasible"):
                co_text = (
                    f" While the requested terms were rejected, an automated counter-offer of ₹{counter_offer['recommended_amount']:,.2f} "
                    f"for {counter_offer['recommended_tenure']} months (EMI: ₹{counter_offer['recommended_emi']:,.2f}, FOIR: {counter_offer['revised_foir']:.2f}%) "
                    f"has been structured for applicant consideration."
                )
            return (
                f"Loan application for {applicant_name} seeking ₹{requested_amount:,.2f} has been declined. "
                f"The underwriting review determined that {reason}. "
                f"Bureau risk rating is recorded as {credit_verdict}"
                + (f" with calculated debt service ratio at {foir:.2f}%." if foir is not None else ".")
                + co_text
            )
        else:  # REFER
            co_text = ""
            if counter_offer and counter_offer.get("feasible"):
                co_text = (
                    f" A pre-evaluated restructuring option of ₹{counter_offer['recommended_amount']:,.2f} "
                    f"at {counter_offer['recommended_tenure']} months is available subject to verification."
                )
            return (
                f"Application {applicant_name} for ₹{requested_amount:,.2f} has been routed to Senior Credit Risk Officers for manual appraisal (REFER). "
                f"Primary referral driver: {reason} "
                f"Credit verification standing: {credit_verdict}. "
                f"No automatic sanction or decline is issued pending document validation and exception approval."
                + co_text
            )


kernel_service = KernelService()

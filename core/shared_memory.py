import copy
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.schemas import AgentStepAudit, SharedApplicantMemorySchema


class SilentOverwriteError(Exception):
    """Raised when an agent attempts to overwrite a previously written section without explicit permission."""
    pass


class SharedApplicantMemory:
    """
    Thread-safe shared memory repository maintaining applicant state and agent audit trail.
    Enforces section immutability by default to prevent silent data clobbering.
    """

    def __init__(self, application_id: str, initial_applicant_data: Optional[Dict[str, Any]] = None):
        self._lock = threading.RLock()
        self.application_id = application_id
        now_iso = datetime.utcnow().isoformat()

        self._data: Dict[str, Any] = {
            "application_id": application_id,
            "applicant": initial_applicant_data or {},
            "document_analysis": {},
            "emi_calculation": {},
            "affordability_analysis": {},
            "credit_analysis": {},
            "counter_offer": None,
            "final_decision": {},
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        self._written_sections: set[str] = set()
        if initial_applicant_data:
            self._written_sections.add("applicant")

        self._audit_trail: List[AgentStepAudit] = []
        self._active_timers: Dict[str, float] = {}

    def start_agent_step(self, agent_name: str, task_description: str) -> None:
        """Mark agent start time for execution timing and audit trail."""
        with self._lock:
            self._active_timers[agent_name] = time.perf_counter()
            audit_entry = AgentStepAudit(
                agent_name=agent_name,
                status="STARTED",
                started_at=datetime.utcnow().isoformat(),
                task_description=task_description,
            )
            self._audit_trail.append(audit_entry)

    def complete_agent_step(
        self,
        agent_name: str,
        status: str,
        output_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> float:
        """Mark agent completion and calculate execution duration in milliseconds."""
        with self._lock:
            start_time = self._active_timers.pop(agent_name, None)
            duration_ms = 0.0
            if start_time is not None:
                duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

            now_iso = datetime.utcnow().isoformat()

            # Find matching recent started step
            found = False
            for step in reversed(self._audit_trail):
                if step.agent_name == agent_name and step.status == "STARTED":
                    step.status = status
                    step.completed_at = now_iso
                    step.execution_time_ms = duration_ms
                    step.output_summary = output_summary or {}
                    step.error_message = error_message
                    found = True
                    break

            if not found:
                self._audit_trail.append(AgentStepAudit(
                    agent_name=agent_name,
                    status=status,
                    started_at=now_iso,
                    completed_at=now_iso,
                    execution_time_ms=duration_ms,
                    task_description=f"Execution of {agent_name}",
                    output_summary=output_summary or {},
                    error_message=error_message
                ))

            self._data["updated_at"] = now_iso
            return duration_ms

    def update_section(
        self,
        section_name: str,
        content: Dict[str, Any],
        allow_overwrite: bool = False
    ) -> None:
        """
        Update a designated section of the shared memory.
        Guards against silent accidental overwrites across agents.
        """
        with self._lock:
            if section_name not in self._data:
                raise KeyError(f"Invalid section name: '{section_name}' is not part of the applicant schema.")

            if section_name in self._written_sections and not allow_overwrite:
                # If existing section has meaningful data, prevent silent overwrite
                existing_val = self._data[section_name]
                if existing_val and existing_val != {}:
                    raise SilentOverwriteError(
                        f"Section '{section_name}' has already been populated. "
                        f"Explicit allow_overwrite=True is required to modify."
                    )

            self._data[section_name] = copy.deepcopy(content)
            self._written_sections.add(section_name)
            self._data["updated_at"] = datetime.utcnow().isoformat()

    def get_section(self, section_name: str) -> Any:
        """Retrieve a deepcopy of a shared memory section to prevent unauthorized in-place mutations."""
        with self._lock:
            if section_name not in self._data:
                raise KeyError(f"Invalid section name: '{section_name}'")
            return copy.deepcopy(self._data[section_name])

    def get_applicant_field(self, field_name: str, default: Any = None) -> Any:
        """Convenience method to access applicant details from applicant or document_analysis."""
        with self._lock:
            applicant = self._data.get("applicant", {})
            if field_name in applicant and applicant[field_name] is not None:
                return applicant[field_name]
            doc = self._data.get("document_analysis", {})
            return doc.get(field_name, default)

    def get_audit_trail(self) -> List[AgentStepAudit]:
        """Retrieve copy of all audit trail items."""
        with self._lock:
            return copy.deepcopy(self._audit_trail)

    def to_dict(self) -> Dict[str, Any]:
        """Export snapshot of memory including audit trail."""
        with self._lock:
            snapshot = copy.deepcopy(self._data)
            snapshot["agent_audit_trail"] = [step.model_dump() for step in self._audit_trail]
            return snapshot

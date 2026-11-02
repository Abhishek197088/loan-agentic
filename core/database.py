import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    Boolean,
    desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

Base = declarative_base()


class ApplicationModel(Base):
    """Database table for storing loan application records and underwriting results."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(64), unique=True, index=True, nullable=False)
    applicant_name = Column(String(255), nullable=False)
    monthly_income = Column(Float, nullable=True)
    existing_emis = Column(Float, default=0.0)
    requested_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    annual_interest_rate = Column(Float, nullable=False)
    calculated_emi = Column(Float, nullable=True)
    foir = Column(Float, nullable=True)
    affordability_verdict = Column(String(32), nullable=False)
    credit_verdict = Column(String(32), nullable=False)
    final_decision = Column(String(32), nullable=False)  # SANCTION, DECLINE, REFER
    counter_offer_json = Column(Text, nullable=True)
    decision_reason = Column(Text, nullable=False)
    justification_paragraph = Column(Text, nullable=False)
    shared_memory_snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "applicant_name": self.applicant_name,
            "monthly_income": self.monthly_income,
            "existing_emis": self.existing_emis,
            "requested_amount": self.requested_amount,
            "tenure_months": self.tenure_months,
            "annual_interest_rate": self.annual_interest_rate,
            "calculated_emi": self.calculated_emi,
            "foir": self.foir,
            "affordability_verdict": self.affordability_verdict,
            "credit_verdict": self.credit_verdict,
            "final_decision": self.final_decision,
            "counter_offer": json.loads(self.counter_offer_json) if self.counter_offer_json else None,
            "decision_reason": self.decision_reason,
            "justification_paragraph": self.justification_paragraph,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentAuditLogModel(Base):
    """Database table for auditing each agent's execution details."""
    __tablename__ = "agent_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(64), index=True, nullable=False)
    agent_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    task_description = Column(Text, nullable=False)
    started_at = Column(String(64), nullable=False)
    completed_at = Column(String(64), nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    output_summary_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "task_description": self.task_description,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time_ms": self.execution_time_ms,
            "output_summary": json.loads(self.output_summary_json) if self.output_summary_json else {},
            "error_message": self.error_message,
        }


# Database engine and session factory
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_application_record(
    db: Session,
    app_id: str,
    name: str,
    income: Optional[float],
    existing_emis: float,
    amount: float,
    tenure: int,
    rate: float,
    emi: Optional[float],
    foir: Optional[float],
    affordability: str,
    credit: str,
    decision: str,
    counter_offer: Optional[Dict[str, Any]],
    reason: str,
    justification: str,
    shared_memory_dict: Dict[str, Any],
    audit_trail: List[Dict[str, Any]]
) -> ApplicationModel:
    """Save or update application and audit trail inside a database transaction."""
    # Check for existing record
    existing = db.query(ApplicationModel).filter(ApplicationModel.application_id == app_id).first()
    if existing:
        app_record = existing
        app_record.applicant_name = name
        app_record.monthly_income = income
        app_record.existing_emis = existing_emis
        app_record.requested_amount = amount
        app_record.tenure_months = tenure
        app_record.annual_interest_rate = rate
        app_record.calculated_emi = emi
        app_record.foir = foir
        app_record.affordability_verdict = affordability
        app_record.credit_verdict = credit
        app_record.final_decision = decision
        app_record.counter_offer_json = json.dumps(counter_offer) if counter_offer else None
        app_record.decision_reason = reason
        app_record.justification_paragraph = justification
        app_record.shared_memory_snapshot = json.dumps(shared_memory_dict)
        app_record.updated_at = datetime.utcnow()
    else:
        app_record = ApplicationModel(
            application_id=app_id,
            applicant_name=name,
            monthly_income=income,
            existing_emis=existing_emis,
            requested_amount=amount,
            tenure_months=tenure,
            annual_interest_rate=rate,
            calculated_emi=emi,
            foir=foir,
            affordability_verdict=affordability,
            credit_verdict=credit,
            final_decision=decision,
            counter_offer_json=json.dumps(counter_offer) if counter_offer else None,
            decision_reason=reason,
            justification_paragraph=justification,
            shared_memory_snapshot=json.dumps(shared_memory_dict),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(app_record)

    # Save audit logs
    for log in audit_trail:
        audit_entry = AgentAuditLogModel(
            application_id=app_id,
            agent_name=log.get("agent_name", "UNKNOWN"),
            status=log.get("status", "COMPLETED"),
            task_description=log.get("task_description", ""),
            started_at=log.get("started_at", ""),
            completed_at=log.get("completed_at", ""),
            execution_time_ms=log.get("execution_time_ms", 0.0),
            output_summary_json=json.dumps(log.get("output_summary", {})),
            error_message=log.get("error_message")
        )
        db.add(audit_entry)

    db.commit()
    db.refresh(app_record)
    return app_record


def get_application(db: Session, app_id: str) -> Optional[ApplicationModel]:
    return db.query(ApplicationModel).filter(ApplicationModel.application_id == app_id).first()


def list_applications_records(
    db: Session,
    decision_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ApplicationModel]:
    query = db.query(ApplicationModel)
    if decision_filter and decision_filter.upper() != "ALL":
        query = query.filter(ApplicationModel.final_decision == decision_filter.upper())
    if search_query:
        query = query.filter(
            (ApplicationModel.application_id.ilike(f"%{search_query}%")) |
            (ApplicationModel.applicant_name.ilike(f"%{search_query}%"))
        )
    return query.order_by(desc(ApplicationModel.created_at)).offset(offset).limit(limit).all()


def get_audit_logs(db: Session, app_id: str) -> List[AgentAuditLogModel]:
    return db.query(AgentAuditLogModel).filter(
        AgentAuditLogModel.application_id == app_id
    ).order_by(AgentAuditLogModel.id.asc()).all()


def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
    """Calculate key financial portfolio metrics for the dashboard."""
    all_apps = db.query(ApplicationModel).all()
    total = len(all_apps)
    if total == 0:
        return {
            "total_applications": 0,
            "sanctioned_count": 0,
            "declined_count": 0,
            "referred_count": 0,
            "average_loan_amount": 0.0,
            "approval_rate": 0.0,
            "total_sanctioned_amount": 0.0
        }

    sanctioned = sum(1 for a in all_apps if a.final_decision == "SANCTION")
    declined = sum(1 for a in all_apps if a.final_decision == "DECLINE")
    referred = sum(1 for a in all_apps if a.final_decision == "REFER")
    total_amount = sum(a.requested_amount for a in all_apps)
    sanctioned_amount = sum(a.requested_amount for a in all_apps if a.final_decision == "SANCTION")
    avg_amount = total_amount / total if total > 0 else 0.0
    approval_rate = (sanctioned / total) * 100 if total > 0 else 0.0

    return {
        "total_applications": total,
        "sanctioned_count": sanctioned,
        "declined_count": declined,
        "referred_count": referred,
        "average_loan_amount": round(avg_amount, 2),
        "approval_rate": round(approval_rate, 2),
        "total_sanctioned_amount": round(sanctioned_amount, 2)
    }

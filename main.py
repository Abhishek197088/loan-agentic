import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from core.config import settings
from core.database import (
    init_db,
    get_db,
    get_application,
    list_applications_records,
    get_audit_logs,
    get_dashboard_metrics,
    ApplicationModel
)
from core.schemas import (
    LoanApplicationInput,
    FinalDecisionResponse,
    EMICalculationResult
)
from tools.emi_calculator import compute_emi
from agents.underwriting_manager import UnderwritingManager
from tools.sample_pdf_generator import generate_sample_application_pdf


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and upload directory exist
    init_db()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Multi-Agent Loan Underwriting System API",
    description="Production-grade multi-agent credit underwriting engine powered by Semantic Kernel.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = UnderwritingManager()


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root route to the interactive presentation and overview."""
    return RedirectResponse(url="/presentation")


@app.get("/presentation", tags=["Presentation"])
async def serve_presentation():
    """Serve the animated HTML5 interactive presentation deck."""
    presentation_path = Path(__file__).parent / "frontend" / "presentation.html"
    if not presentation_path.exists():
        raise HTTPException(status_code=404, detail="Presentation file not found.")
    return FileResponse(str(presentation_path), media_type="text/html")


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Multi-Agent Loan Underwriting System",
        "environment": settings.environment,
        "llm_provider": "OpenAI/Semantic Kernel" if settings.openai_api_key else "Rule-Based Fallback",
        "max_foir_percent": settings.max_foir_percent
    }


@app.get("/api/v1/metrics", tags=["Dashboard"])
async def dashboard_metrics(db: Session = Depends(get_db)):
    """Fetch aggregated credit underwriting metrics."""
    return get_dashboard_metrics(db)


@app.post("/api/v1/calculate-emi", response_model=EMICalculationResult, tags=["Calculators"])
async def calculate_emi_endpoint(
    principal: float = Query(..., gt=0, description="Principal loan amount"),
    annual_interest_rate: float = Query(..., ge=0, description="Annual interest rate in %"),
    tenure_months: int = Query(..., gt=0, le=360, description="Tenure in months")
):
    """Deterministic reducing-balance EMI calculation endpoint."""
    try:
        return compute_emi(
            principal=principal,
            annual_interest_rate=annual_interest_rate,
            tenure_months=tenure_months
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/upload-document", tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """Validate and upload PDF proof document with file size and type guards."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (.pdf) are permitted."
        )

    # File size validation (stream read in chunks)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    temp_filename = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    target_path = settings.uploads_dir / temp_filename

    total_bytes = 0
    with open(target_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                buffer.close()
                if target_path.exists():
                    os.remove(target_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Uploaded file exceeds maximum permitted size of {settings.max_upload_size_mb}MB."
                )
            buffer.write(chunk)

    return {
        "filename": file.filename,
        "saved_path": str(target_path),
        "size_bytes": total_bytes,
        "status": "UPLOAD_SUCCESS"
    }


@app.post("/api/v1/applications", response_model=FinalDecisionResponse, tags=["Underwriting"])
async def submit_application(
    application: LoanApplicationInput,
    check_duplicate: bool = Query(True, description="Enforce duplicate check"),
    db: Session = Depends(get_db)
):
    """
    Submit a loan application to the Underwriting Manager.
    Coordinates all six specialized agents through shared memory.
    """
    # Duplicate check
    if check_duplicate:
        existing = get_application(db, application.application_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application ID '{application.application_id}' already exists in the system. Use a unique ID or update existing."
            )

    try:
        response = await manager.process_application(application, persist_db=True)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Underwriting execution failed: {str(e)}")


@app.get("/api/v1/applications/{application_id}", tags=["Underwriting"])
async def retrieve_application(application_id: str, db: Session = Depends(get_db)):
    """Retrieve application underwriting record and agent audit trail."""
    app_record = get_application(db, application_id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found."
        )

    audit_logs = get_audit_logs(db, application_id)
    data = app_record.to_dict()
    data["agent_audit_trail"] = [log.to_dict() for log in audit_logs]
    return data


@app.get("/api/v1/applications", tags=["Underwriting"])
async def list_applications(
    decision: Optional[str] = Query(None, description="Filter by decision: SANCTION, DECLINE, REFER, or ALL"),
    search: Optional[str] = Query(None, description="Search by application ID or applicant name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List historical loan applications with search and filtering."""
    records = list_applications_records(
        db,
        decision_filter=decision,
        search_query=search,
        limit=limit,
        offset=offset
    )
    return [r.to_dict() for r in records]


@app.post("/api/v1/seed-demo-cases", tags=["Demonstration"])
async def seed_demo_cases(db: Session = Depends(get_db)):
    """
    Seed and execute the 5 required institutional demonstration cases:
    Case 1: Eligible applicant — SANCTION (Rahul Sharma, APP001)
    Case 2: High EMI burden — DECLINE with Counter-Offer (Priya Patel, APP002)
    Case 3: Missing income — REFER immediately (Amit Kumar, APP003)
    Case 4: Credit default — DECLINE verified bureau default (Vikram Singh, APP004)
    Case 5: Affordability failure — Generate valid counter-offer (Sneha Rao, APP005)
    """
    demo_cases = [
        # Case 1: Rahul Sharma - Eligible -> SANCTION
        {
            "application_id": "APP001",
            "applicant_name": "Rahul Sharma",
            "monthly_income": 60000.0,
            "existing_emis": 8000.0,
            "requested_amount": 500000.0,
            "tenure_months": 60,
            "annual_interest_rate": 12.0
        },
        # Case 2: Priya Patel - High EMI Burden -> DECLINE with Counter-Offer
        {
            "application_id": "APP002",
            "applicant_name": "Priya Patel",
            "monthly_income": 75000.0,
            "existing_emis": 24000.0,
            "requested_amount": 700000.0,
            "tenure_months": 36,
            "annual_interest_rate": 12.0
        },
        # Case 3: Amit Kumar - Missing Income -> REFER immediately
        {
            "application_id": "APP003",
            "applicant_name": "Amit Kumar",
            "monthly_income": None,
            "existing_emis": 5000.0,
            "requested_amount": 300000.0,
            "tenure_months": 48,
            "annual_interest_rate": 11.5
        },
        # Case 4: Vikram Singh - Credit Default -> DECLINE
        {
            "application_id": "APP004",
            "applicant_name": "Vikram Singh",
            "monthly_income": 90000.0,
            "existing_emis": 10000.0,
            "requested_amount": 400000.0,
            "tenure_months": 36,
            "annual_interest_rate": 12.0
        },
        # Case 5: Sneha Rao - Affordability Failure with Counter-Offer
        {
            "application_id": "APP005",
            "applicant_name": "Sneha Rao",
            "monthly_income": 50000.0,
            "existing_emis": 12000.0,
            "requested_amount": 600000.0,
            "tenure_months": 48,
            "annual_interest_rate": 12.0
        }
    ]

    results = []
    for c in demo_cases:
        # Generate sample PDF for each case
        pdf_path = settings.uploads_dir / f"demo_{c['application_id']}.pdf"
        generate_sample_application_pdf(
            file_path=str(pdf_path),
            applicant_name=c["applicant_name"],
            monthly_income=c["monthly_income"],
            existing_emis=c["existing_emis"],
            requested_amount=c["requested_amount"],
            tenure_months=c["tenure_months"],
            annual_interest_rate=c["annual_interest_rate"],
        )

        app_input = LoanApplicationInput(
            application_id=c["application_id"],
            applicant_name=c["applicant_name"],
            monthly_income=c["monthly_income"],
            existing_emis=c["existing_emis"],
            requested_amount=c["requested_amount"],
            tenure_months=c["tenure_months"],
            annual_interest_rate=c["annual_interest_rate"],
            uploaded_document_path=str(pdf_path)
        )
        res = await manager.process_application(app_input, persist_db=True)
        results.append(res.model_dump())

    return {
        "message": "Successfully seeded and evaluated all 5 demonstration cases.",
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

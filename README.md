# Multi-Agent Loan Underwriting System

An advanced, production-style, multi-agent financial credit underwriting system built with **Python 3.11+**, **Microsoft Semantic Kernel**, **FastAPI**, **SQLite / SQLAlchemy**, and **Streamlit**.

The system automates the appraisal of commercial and personal credit applications through a **Manager-Worker Delegation Architecture** featuring six specialized AI agents, immutable shared applicant memory, deterministic financial calculations, prompt injection defense, automated counter-offer generation, and full audit logging.

---

## Architecture Overview

```
                         ┌────────────────────────────────────────┐
                         │   AGENT 6: UNDERWRITING MANAGER        │
                         │   (Orchestrator & Policy Arbiter)      │
                         └──────────────────┬─────────────────────┘
                                            │
        ┌───────────────────┬───────────────┼───────────────┬───────────────────┐
        │                   │               │               │                   │
        ▼                   ▼               ▼               ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   AGENT 1:    │   │   AGENT 2:    │   │   AGENT 3:    │   │   AGENT 4:    │   │   AGENT 5:    │
│ DOCUMENT AGENT│   │   EMI AGENT   │   │ AFFORDABILITY │   │ CREDIT-HISTORY│   │ COUNTER-OFFER │
│ (PDF Extract) │   │ (Reducing Bal)│   │  (FOIR <= 40%)│   │ (Bureau Check)│   │ (Restructure) │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │               │               │                   │
        └───────────────────┴───────────────┴───────────────┴───────────────────┘
                                            │
                                            ▼
                         ┌────────────────────────────────────────┐
                         │       SHARED APPLICANT MEMORY          │
                         │ (Thread-safe, Non-silent Overwrite,    │
                         │  Audit Timers, SQLite Persistence)     │
                         └────────────────────────────────────────┘
```

---

## Key Features

1. **Manager-Worker Multi-Agent Orchestration**:
   - **Agent 1 (Document Agent)**: Accepts loan details, reads uploaded PDF documents, sanitizes text against prompt injection attacks, extracts financial fields, and catalogs discrepancies without fabricating data.
   - **Agent 2 (EMI Computation Agent)**: Deterministically calculates monthly EMI, total interest, and total repayment using the reducing-balance formula:
     $$\text{EMI} = \frac{P \times r \times (1+r)^n}{(1+r)^n - 1}$$
     Never delegates mathematical calculations to an LLM. Handles zero-interest loans separately.
   - **Agent 3 (Affordability Agent)**: Evaluates Fixed Obligation to Income Ratio (FOIR):
     $$\text{Total Debt} = \text{Existing EMIs} + \text{Proposed EMI}$$
     $$\text{FOIR} = \left(\frac{\text{Total Debt}}{\text{Net Monthly Income}}\right) \times 100$$
     Enforces institutional ceiling: $\text{FOIR} \le 40\% \implies \text{PASS}$, $\text{FOIR} > 40\% \implies \text{FAIL}$. If monthly income is missing, immediately yields $\text{REFER}$.
   - **Agent 4 (Credit-History Agent)**: Queries historical bureau credit records (`data/credit_history.json`). Flags verified defaults or fraud ($\text{DECLINE}$), unresolved delinquencies ($\text{REFER}$), and clean records ($\text{PASS}$). Unmatched records return $\text{UNKNOWN}$ and are referred for manual verification.
   - **Agent 5 (Counter-Offer Worker)**: Automatically activates when requested loan terms fail affordability. Calculates the maximum affordable principal and explores tenure extension up to 84 months, guaranteeing that the proposed EMI strictly satisfies $\text{FOIR} \le 40\%$ and never exceeds the requested amount.
   - **Agent 6 (Underwriting Manager)**: Central coordinator. Coordinates agents in a strictly controlled sequence, halts immediately if income is missing, resolves conflicting recommendations into a final decision ($\text{SANCTION}$, $\text{DECLINE}$, or $\text{REFER}$), synthesizes audit-ready executive justifications via Microsoft Semantic Kernel, and commits transaction records to SQLite.

2. **Microsoft Semantic Kernel Framework Integration**:
   - Leverages `semantic-kernel` 1.46.0 with `OpenAIChatCompletion` connectors for executive justification synthesis.
   - Transparent, seamless **Rule-Based Fallback Mode** when running offline or without an OpenAI API key.

3. **Enterprise Security & Safeguards**:
   - Adversarial prompt injection defense against token manipulation in uploaded documents.
   - Pydantic v2 strict input validation (bounds on principal, tenure, income).
   - PDF file type and 5MB payload size validation.
   - Shared memory immutability guards (`SilentOverwriteError`) preventing cross-agent data clobbering.
   - SQLite relational persistence with transaction rollback safety.

4. **Fintech Streamlit Dashboard**:
   - Executive Dashboard with KPI cards, approval ratios, and portfolio analytics.
   - Application Intake with 1-click test personas and PDF document upload.
   - Live Agent Observability pipeline visualizer with millisecond execution timers.
   - Interactive Reducing-Balance EMI Calculator with amortization charts.
   - Full Application History with search and decision filters.

---

## Project Structure

```
loan-underwriting-system/
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── kernel_service.py       # Semantic Kernel & LLM connectors
│   ├── document_agent.py       # Agent 1: PDF & field extraction
│   ├── emi_agent.py            # Agent 2: Deterministic EMI calculator
│   ├── affordability_agent.py  # Agent 3: FOIR & debt evaluation
│   ├── credit_history_agent.py # Agent 4: Credit bureau appraisal
│   ├── counter_offer_agent.py  # Agent 5: Loan restructuring worker
│   └── underwriting_manager.py # Agent 6: Master coordinator
│
├── core/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings & environment vars
│   ├── database.py             # SQLite SQLAlchemy models & sessions
│   ├── policies.py             # Risk policy constants & rules
│   ├── schemas.py              # Pydantic validation & response schemas
│   └── shared_memory.py        # Thread-safe applicant memory & audit trail
│
├── tools/
│   ├── __init__.py
│   ├── emi_calculator.py       # Reducing-balance & inverse EMI math
│   ├── affordability_calculator.py # FOIR & capacity math
│   ├── document_extractor.py   # PDF text & prompt injection defense
│   └── sample_pdf_generator.py # Test PDF salary slip generator
│
├── data/
│   └── credit_history.json     # Historical credit bureau dataset
│
├── frontend/
│   └── app.py                  # Streamlit fintech dashboard
│
├── tests/
│   ├── conftest.py
│   ├── test_emi.py             # Tests 1, 4, 9, 11, 12
│   ├── test_affordability.py   # Tests 1, 2, 3, 5
│   ├── test_agents.py          # Tests 6, 7, 8 & PDF injection defense
│   └── test_manager.py         # End-to-end orchestration & Test 10
│
├── main.py                     # FastAPI REST API & lifespan manager
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (`venv` or `conda`)

### Step 1: Clone and Set Up Virtual Environment
```bash
cd loan-underwriting-system
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: Insert your `OPENAI_API_KEY` in `.env` to enable live LLM executive synthesis. If left empty, the system automatically operates in verified Rule-Based Fallback Mode with 100% functionality).*

---

## Running the Application

### 1. Launch FastAPI Backend
```bash
source .venv/bin/activate
cd loan-underwriting-system
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 2. Launch Streamlit Frontend Dashboard
In a separate terminal:
```bash
source .venv/bin/activate
cd loan-underwriting-system
streamlit run frontend/app.py --server.port 8501
```
- Access the Web Dashboard at: [http://localhost:8501](http://localhost:8501)

---

## Automated Test Suite

Run the full pytest suite containing all 12 required institutional test cases:
```bash
source .venv/bin/activate
cd loan-underwriting-system
pytest -v
```

### Test Cases Covered:
1. **Normal application with good affordability**: Verified income, low FOIR (31.87%), clean bureau $\implies$ `SANCTION`.
2. **Application exceeding 40% FOIR**: Debt service exceeds limit $\implies$ `FAIL`.
3. **Missing monthly income**: Evaluated without assumptions $\implies$ immediate `REFER`.
4. **Zero-interest loan**: Validates deterministic $P/n$ calculation and $0$ interest.
5. **Existing EMI exceeding income capacity**: Existing debt consumes $>40\%$ limit $\implies$ `FAIL`.
6. **Unknown credit history**: Unmatched bureau applicant $\implies$ `UNKNOWN` & `REFER`.
7. **Verified fraud flag**: Credit bureau fraud record $\implies$ `DECLINE`.
8. **Counter-offer generation**: Restructures unaffordable loans to compliant $\text{FOIR} \le 40\%$.
9. **Maximum affordable loan amount**: Mathematical inversion of reducing-balance formula.
10. **Duplicate application check**: Verifies transaction integrity and duplicate prevention in SQLite.
11. **Invalid loan amount**: Non-positive principal triggers validation error.
12. **Invalid tenure**: Non-positive tenure triggers validation error.

---

## Institutional Demonstration Cases

Click **⚡ Seed 5 Demo Cases** on the dashboard sidebar or execute `POST /api/v1/seed-demo-cases` to view the 5 demonstration profiles:

| Case | Applicant | Income | Existing EMI | Requested | Tenure | Calculated EMI | FOIR | Decision | Output Rationale |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Case 1** | Rahul Sharma (`APP001`) | ₹60,000 | ₹8,000 | ₹500,000 | 60m | ₹11,122.22 | **31.87%** | **SANCTION** | Verified income, obligations within 40% ceiling, clean bureau history. |
| **Case 2** | Priya Patel (`APP002`) | ₹75,000 | ₹24,000 | ₹700,000 | 36m | ₹23,250.02 | **63.00%** | **DECLINE** *(with Counter-Offer)* | Exceeds 40% FOIR ceiling. Restructured counter-offer of ₹339,000 @ 84m (EMI ₹5,984.28, FOIR 39.98%) provided. |
| **Case 3** | Amit Kumar (`APP003`) | *Missing* | ₹5,000 | ₹300,000 | 48m | *N/A* | *N/A* | **REFER** | Immediate halt due to unverified income. Never estimates or fabricates income. |
| **Case 4** | Vikram Singh (`APP004`) | ₹90,000 | ₹10,000 | ₹400,000 | 36m | ₹13,285.72 | **25.87%** | **DECLINE** | Confirmed historical credit default flagged in bureau records. Hard policy rejection. |
| **Case 5** | Sneha Rao (`APP005`) | ₹50,000 | ₹12,000 | ₹600,000 | 48m | ₹15,800.30 | **55.60%** | **DECLINE** *(with Counter-Offer)* | Exceeds 40% FOIR ceiling. Restructured counter-offer of ₹453,000 @ 84m (EMI ₹7,996.69, FOIR 39.99%) provided. |

---

## Final Output Schema (Section 8 Format)

```json
{
  "application_id": "APP001",
  "decision": "SANCTION",
  "requested_amount": 500000.0,
  "emi": 11122.22,
  "existing_emi": 8000.0,
  "monthly_income": 60000.0,
  "foir": 31.87,
  "affordability": "PASS",
  "credit_history": "PASS",
  "counter_offer": null,
  "reason": "The applicant has verified income, repayment obligations are within the configured affordability limit (FOIR <= 40%), and credit history contains no identified red flags."
}
```

---

## Regulatory Compliance & Fairness Statement
*This multi-agent underwriting platform is designed as an intelligent decision-support system for credit risk committees. Final lending authority is subject to human review, organizational risk tolerances, regulatory fair lending compliance, and institutional auditing.*

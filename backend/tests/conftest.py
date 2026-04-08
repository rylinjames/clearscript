"""
Pytest fixtures for ClearScript backend tests.

Tests run with `backend/` as the working directory:
    cd backend && pytest

The fixtures here:
  1. Put `backend/` on sys.path so `from services.x import ...` resolves.
  2. Set a fake OPENAI_API_KEY so the OpenAI client can initialize without
     exploding (the actual network calls are monkeypatched per-test).
  3. Point the SQLite DB at a temp file so tests don't clobber real data.
  4. Provide a FastAPI TestClient + canned AI response fixtures.
"""
import os
import sys
import json
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set env vars BEFORE any backend modules import. ai_service reads these at
# module import time via load_dotenv, and _get_client reads OPENAI_API_KEY
# lazily — so a fake key here just has to exist, it never gets used because
# tests monkeypatch the actual OpenAI call.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-unit-tests")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


# ─── Canned AI responses ────────────────────────────────────────────────────

FAKE_CONTRACT_ANALYSIS = {
    "rebate_passthrough": {
        "found": True,
        "percentage": "85% of eligible rebates",
        "rating": "pbm_favorable",
        "details": "Narrow definition excludes admin fees and volume bonuses",
    },
    "spread_pricing": {
        "found": True,
        "caps": "None",
        "rating": "pbm_favorable",
        "details": "PBM retains full spread with no transparency",
    },
    "audit_rights": {
        "found": True,
        "scope": "Claims data only",
        "rating": "pbm_favorable",
        "details": "Does not include rebate contracts or pharmacy reimbursement",
    },
    "mac_pricing": {"found": True, "rating": "neutral", "details": "Monthly updates"},
    "formulary_clauses": {"found": True, "rating": "neutral", "details": "30-day notice"},
    "termination_provisions": {"found": True, "rating": "neutral", "details": "90-day notice"},
    "gag_clauses": {"found": False, "rating": "employer_favorable", "details": "None detected"},
    "overall_risk_score": 72,
    "weighted_assessment": {
        "deal_score": 58,
        "weighted_risk_score": 72,
        "risk_level": "high",
    },
    "deal_diagnosis": "Contract is materially PBM-favorable and needs renegotiation.",
    "financial_exposure": {
        "summary": "Estimated $420k annual leakage across spread + rebate retention.",
        "mode": "estimate",
        "spread_exposure": {"estimate": 240000},
    },
    "control_posture": {
        "label": "Weak",
        "summary": "Employer has minimal contractual leverage.",
    },
    "structural_risk_override": {
        "triggered": False,
        "level": "medium",
        "headline": "No structural override triggered",
    },
    "top_risks": [
        {"title": "Unlimited spread", "severity": "high"},
        {"title": "Narrow rebate definition", "severity": "high"},
        {"title": "Limited audit scope", "severity": "medium"},
    ],
    "immediate_actions": [
        "Request audit under new DOL rule",
        "Demand rebate definition expansion",
        "Cap spread at zero",
    ],
    "benchmark_observations": [
        "Spread cap: absent vs industry best-in-class of $0",
        "Rebate passthrough: 85% vs industry best of 100%",
    ],
}

FAKE_AUDIT_LETTER = {
    "letter_text": (
        "Dear OptumRx Compliance Team,\n\n"
        "Pursuant to the DOL transparency rule (29 CFR 2520.103-1) and HR 7148, "
        "Acme Corporation hereby exercises its audit rights under Section 8.2 of "
        "the Pharmacy Benefit Management Agreement dated January 15, 2024.\n\n"
        "Please provide the following within ten (10) business days: ...\n\n"
        "Sincerely,\nAcme Corporation Benefits Team"
    ),
    "citations": ["29 CFR 2520.103-1", "HR 7148 Section 4(b)"],
    "data_requests": [
        "Complete rebate contracts with manufacturers",
        "Pharmacy reimbursement rates by NDC",
        "MAC list updates for the audit period",
    ],
    "response_deadline_days": 10,
}

FAKE_DISCLOSURE_ANALYSIS = {
    "completeness_score": 62,
    "required_items": [
        {"item": "Direct compensation", "present": True},
        {"item": "Indirect compensation", "present": False},
        {"item": "Rebate retention details", "present": False},
    ],
    "missing_items": ["Indirect compensation", "Rebate retention details"],
    "gap_report": "Disclosure is missing 2 of 3 required DOL items.",
}


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """
    Give every test its own empty SQLite file.

    Two things have to happen for this to work after the SQLite/Postgres
    abstraction was added:

      1. Force the database backend to SQLite by clearing SUPABASE_DB_URL
         from the env. Otherwise a developer with the env var set locally
         (for debugging Postgres) would have their tests hit the real
         Supabase database — disastrous.

      2. Patch the SQLite path on `services.database` (and the legacy
         `services.db_service.DB_PATH` re-export) to point at a temp
         file unique to this test, so concurrent tests don't collide
         and tests don't see each other's writes.

    autouse=True because even tests that don't touch the DB end up
    triggering startup code that reads from it.
    """
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    import services.database as database
    import services.db_service as db_service

    test_db = tmp_path / "clearscript_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    monkeypatch.setattr(db_service, "DB_PATH", test_db)

    # Create the schema on the isolated DB. Without this, routers that
    # call save_contract_analysis / save_claims hit "no such table".
    db_service._ensure_db()
    yield test_db


@pytest.fixture
def client():
    """FastAPI TestClient. Imports main after env vars + DB patch are in place."""
    from fastapi.testclient import TestClient
    import main  # noqa: WPS433
    return TestClient(main.app)


@pytest.fixture
def mock_ai(monkeypatch):
    """
    Monkeypatch every OpenAI-touching function with canned responses.

    Use this on any test that hits a router which would otherwise call the
    real OpenAI API. Keeps tests fast, offline, and deterministic.
    """
    async def fake_run_contract_pipeline(text: str):
        return dict(FAKE_CONTRACT_ANALYSIS)

    async def fake_generate_audit_letter(contract_data, findings):
        return dict(FAKE_AUDIT_LETTER)

    async def fake_analyze_disclosure(text: str):
        return dict(FAKE_DISCLOSURE_ANALYSIS)

    async def fake_analyze_contract(text: str):
        return dict(FAKE_CONTRACT_ANALYSIS)

    async def fake_generate(system_prompt, user_prompt, max_tokens=3000):
        return json.dumps(FAKE_CONTRACT_ANALYSIS)

    # Patch at the module the routers import from, not the origin — FastAPI
    # routers have already done `from services.x import fn` at import time.
    import services.ai_service as ai_svc
    import services.pipeline_service as pipe_svc
    import routers.contracts as contracts_router
    import routers.audit as audit_router

    monkeypatch.setattr(ai_svc, "_generate", fake_generate, raising=False)
    monkeypatch.setattr(ai_svc, "generate_audit_letter", fake_generate_audit_letter, raising=False)
    monkeypatch.setattr(ai_svc, "analyze_contract", fake_analyze_contract, raising=False)
    if hasattr(ai_svc, "analyze_disclosure"):
        monkeypatch.setattr(ai_svc, "analyze_disclosure", fake_analyze_disclosure, raising=False)

    monkeypatch.setattr(pipe_svc, "run_contract_pipeline", fake_run_contract_pipeline, raising=False)
    monkeypatch.setattr(contracts_router, "run_contract_pipeline", fake_run_contract_pipeline, raising=False)
    monkeypatch.setattr(audit_router, "generate_audit_letter", fake_generate_audit_letter, raising=False)

    return {
        "contract": FAKE_CONTRACT_ANALYSIS,
        "audit_letter": FAKE_AUDIT_LETTER,
        "disclosure": FAKE_DISCLOSURE_ANALYSIS,
    }


@pytest.fixture
def sample_contract_text() -> bytes:
    """A minimal PBM contract text blob, long enough to bypass the `< 50 chars` mock fallback."""
    return (
        "PHARMACY BENEFIT MANAGEMENT AGREEMENT\n"
        "Between Acme Corporation and OptumRx, dated January 15, 2024.\n\n"
        "SECTION 3. REBATES. PBM shall pass through 85% of eligible manufacturer rebates.\n"
        "SECTION 5. SPREAD PRICING. No cap on spread retained by PBM.\n"
        "SECTION 8. AUDIT RIGHTS. Plan Sponsor may audit claims data once per year.\n"
        "SECTION 12. TERMINATION. 90 days written notice required for termination without cause.\n"
    ).encode("utf-8")


@pytest.fixture
def sample_claims_csv() -> bytes:
    """A minimal valid claims CSV matching the REQUIRED_COLUMNS in claims_upload.py."""
    header = (
        "claim_id,drug_name,ndc,quantity,days_supply,date_filled,channel,"
        "pharmacy_name,pharmacy_npi,pharmacy_zip,plan_paid,pharmacy_reimbursed,"
        "awp,nadac_price,rebate_amount,formulary_tier"
    )
    rows = [
        "CLM-001,Atorvastatin,00071015623,30,30,2025-01-05,retail,CVS Pharmacy,1234567890,10001,45.20,12.50,80.00,9.80,5.25,1",
        "CLM-002,Humira,00074779902,2,28,2025-01-12,specialty,Accredo,9876543210,63101,6420.00,5800.00,7200.00,5750.00,1200.00,4",
        "CLM-003,Metformin,00093105001,60,30,2025-01-18,mail,Express Scripts Mail,5555555555,85001,8.40,3.10,18.00,2.80,0.00,1",
    ]
    return ("\n".join([header, *rows]) + "\n").encode("utf-8")

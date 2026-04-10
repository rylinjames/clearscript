"""
ClearScript — Plan Intelligence Platform
FastAPI backend. Product 1: Contract Reader.
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clearscript")

# ─── Product 1: Contract Reader ───────────────────────────────────────────
from routers import (
    contracts,
    disclosure,
    spc,
    compliance,
    audit,
    claims_upload,
    benchmarks,
    cms_benchmark,
    drug_lookup,
    formulary,
    exclusion_list,
    batch_formulary,
    reports,
    audit_timeline,
    spread,
    rebates,
    ndc_analysis,
    network,
    prior_auth,
    provider_anomaly,
    copay_accumulator,
    cms_data,
    feedback,
)

app = FastAPI(
    title="ClearScript — Plan Intelligence",
    description="AI-powered PBM contract analysis, disclosure auditing, and plan document cross-referencing for employer health plan sponsors.",
    version="1.0.0",
)

# CORS
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error on {request.method} {request.url.path}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": "Internal server error"})


# ─── Product 1: Contract Reader ───────────────────────────────────────────
app.include_router(contracts.router)
app.include_router(disclosure.router)
app.include_router(spc.router)
app.include_router(compliance.router)
app.include_router(audit.router)
app.include_router(claims_upload.router)
app.include_router(benchmarks.router)
app.include_router(cms_benchmark.router)
app.include_router(drug_lookup.router)
app.include_router(formulary.router)
app.include_router(exclusion_list.router)
app.include_router(batch_formulary.router)
app.include_router(reports.router)
app.include_router(audit_timeline.router)
app.include_router(spread.router)
app.include_router(rebates.router)
app.include_router(ndc_analysis.router)
app.include_router(network.router)
app.include_router(prior_auth.router)
app.include_router(provider_anomaly.router)
app.include_router(copay_accumulator.router)
app.include_router(cms_data.router)
app.include_router(feedback.router)


@app.get("/")
async def root():
    return {
        "name": "ClearScript — Plan Intelligence",
        "version": "1.0.0",
        "product": "Plan Intelligence Platform",
        "features": [
            {"id": 1, "name": "Contract Intake & Parsing",        "endpoint": "POST /api/contracts/upload"},
            {"id": 2, "name": "Plan Document Parser (SBC/SPD/EOC)","endpoint": "POST /api/contracts/upload-plan-document"},
            {"id": 3, "name": "Cross-Reference Analysis",          "endpoint": "POST /api/contracts/cross-reference"},
            {"id": 4, "name": "Disclosure Analyzer",               "endpoint": "POST /api/disclosure/analyze"},
            {"id": 5, "name": "Audit Request Generator",           "endpoint": "POST /api/audit/generate"},
            {"id": 6, "name": "Compliance Deadline Tracker",       "endpoint": "GET /api/compliance/deadlines"},
            {"id": 7, "name": "SPC Parser",                        "endpoint": "POST /api/spc/parse"},
            {"id": 8, "name": "Claims Upload",                     "endpoint": "POST /api/claims/upload"},
            {"id": 9, "name": "Benchmarking Dashboard",            "endpoint": "GET /api/benchmarks/data"},
            {"id": 10, "name": "CMS Benchmark Data",               "endpoint": "GET /api/cms-benchmark/partd-stats"},
            {"id": 11, "name": "Drug Lookup",                      "endpoint": "GET /api/drug-lookup/search"},
            {"id": 12, "name": "Formulary Analysis",               "endpoint": "GET /api/formulary/analysis"},
            {"id": 13, "name": "Exclusion List Analyzer",          "endpoint": "POST /api/exclusion-list/parse"},
            {"id": 14, "name": "Batch Formulary Processor",        "endpoint": "POST /api/batch-formulary/process"},
            {"id": 15, "name": "Report Auditor",                   "endpoint": "GET /api/reports/audit"},
            {"id": 16, "name": "Audit Timeline Planner",           "endpoint": "GET /api/audit-timeline/template"},
            {"id": 17, "name": "Spread Pricing Detector",          "endpoint": "GET /api/spread/analysis"},
            {"id": 18, "name": "Rebate Tracker",                   "endpoint": "GET /api/rebates/analysis"},
            {"id": 19, "name": "NDC vs J-Code Analysis",           "endpoint": "GET /api/ndc-analysis/analysis"},
            {"id": 20, "name": "Network Adequacy Analyzer",        "endpoint": "POST /api/network/analyze"},
            {"id": 21, "name": "Prior Authorization Analyzer",     "endpoint": "GET /api/prior-auth/analysis"},
            {"id": 22, "name": "Provider Anomaly Detection",       "endpoint": "GET /api/provider-anomalies/analysis"},
            {"id": 23, "name": "Copay Accumulator Analyzer",       "endpoint": "GET /api/copay-accumulator/analysis"},
        ],
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Aggregate stats for the dashboard — all real data, no placeholders."""
    from services.db_service import (
        list_contract_analyses, load_latest_contract_analysis,
        load_claims_for_contract, load_plan_doc, load_cross_reference,
    )

    # Load all contracts with their enrichment status
    contracts_list = []
    try:
        contracts_list = list_contract_analyses(limit=50)
    except Exception:
        pass

    # For each contract, check what's been uploaded
    contracts_with_status = []
    for c in contracts_list:
        cid = c.get("id")
        has_claims = False
        has_plan_doc = False
        has_cross_ref = False
        notice_deadline = None
        try:
            has_claims = bool(load_claims_for_contract(cid))
        except Exception:
            pass
        try:
            has_plan_doc = bool(load_plan_doc(cid))
        except Exception:
            pass
        try:
            has_cross_ref = bool(load_cross_reference(cid))
        except Exception:
            pass
        # Extract notice deadline from the analysis JSON if available
        try:
            import json
            analysis = json.loads(c.get("analysis_json", "{}") if "analysis_json" in c else "{}")
            ci = analysis.get("contract_identification", {})
            if isinstance(ci, dict):
                notice_deadline = ci.get("notice_deadline_date")
        except Exception:
            pass
        contracts_with_status.append({
            "id": cid,
            "filename": c.get("filename"),
            "analysis_date": c.get("analysis_date"),
            "deal_score": c.get("deal_score"),
            "risk_level": c.get("risk_level"),
            "has_claims": has_claims,
            "has_plan_doc": has_plan_doc,
            "has_cross_ref": has_cross_ref,
            "notice_deadline": notice_deadline,
        })

    latest_analysis = None
    try:
        latest_analysis = load_latest_contract_analysis()
    except Exception:
        latest_analysis = None

    latest = (latest_analysis or {}).get("analysis", {}) if latest_analysis else {}
    if isinstance(latest, dict) and latest:
        try:
            latest = enrich_contract_analysis(dict(latest))
        except Exception as e:
            logger.warning(f"enrich_contract_analysis failed on dashboard read: {e}")
            # Fall back to the raw (un-enriched) analysis so the dashboard
            # still renders something instead of 500-ing the whole page.
    weighted = latest.get("weighted_assessment", {}) if isinstance(latest, dict) else {}
    exposure = latest.get("financial_exposure", {}) if isinstance(latest, dict) else {}
    top_risks = latest.get("top_risks", []) if isinstance(latest, dict) else []
    immediate_actions = latest.get("immediate_actions", []) if isinstance(latest, dict) else []
    control_posture = latest.get("control_posture", {}) if isinstance(latest, dict) else {}
    structural_override = latest.get("structural_risk_override", {}) if isinstance(latest, dict) else {}
    benchmark_observations = latest.get("benchmark_observations", []) if isinstance(latest, dict) else []

    return {
        "contracts_parsed": len(contracts_list),
        "contracts": contracts_with_status,
        "latest_analysis": {
            "filename": latest_analysis.get("filename") if latest_analysis else None,
            "analysis_date": latest_analysis.get("analysis_date") if latest_analysis else None,
            "deal_score": weighted.get("deal_score"),
            "risk_level": weighted.get("risk_level"),
            "deal_diagnosis": latest.get("deal_diagnosis") if isinstance(latest, dict) else None,
            "control_posture_label": control_posture.get("label") if isinstance(control_posture, dict) else None,
            "control_posture_summary": control_posture.get("summary") if isinstance(control_posture, dict) else None,
        } if latest_analysis else None,
    }


@app.on_event("startup")
async def restore_claims_on_startup():
    try:
        await claims_upload.restore_persisted_claims()
    except Exception as e:
        logger.debug(f"Claims restore skipped on startup: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

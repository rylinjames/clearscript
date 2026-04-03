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
)

# ─── Future Products (commented out) ──────────────────────────────────────
# Product 2: Benchmarking Reports
# from routers import benchmarks, cms_benchmark, drug_lookup

# Product 3: Formulary Intelligence
# from routers import formulary, exclusion_list, batch_formulary

# Product 4: Audit Package
# from routers import reports, audit_timeline

# Product 5: Analytics Suite
# from routers import spread, rebates, ndc_analysis, network, prior_auth, provider_anomaly, copay_accumulator, claims_upload

# Shared
# from routers import cms_data

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

# ─── Future Products (commented out) ──────────────────────────────────────
# app.include_router(benchmarks.router)
# app.include_router(cms_benchmark.router)
# app.include_router(drug_lookup.router)
# app.include_router(formulary.router)
# app.include_router(exclusion_list.router)
# app.include_router(batch_formulary.router)
# app.include_router(reports.router)
# app.include_router(audit_timeline.router)
# app.include_router(spread.router)
# app.include_router(rebates.router)
# app.include_router(ndc_analysis.router)
# app.include_router(network.router)
# app.include_router(prior_auth.router)
# app.include_router(provider_anomaly.router)
# app.include_router(copay_accumulator.router)
# app.include_router(claims_upload.router)
# app.include_router(cms_data.router)


@app.get("/")
async def root():
    return {
        "name": "ClearScript — Plan Intelligence",
        "version": "1.0.0",
        "product": "Contract Reader",
        "features": [
            {"id": 1, "name": "Contract Intake & Parsing",        "endpoint": "POST /api/contracts/upload"},
            {"id": 2, "name": "Plan Document Parser (SBC/SPD/EOC)","endpoint": "POST /api/contracts/upload-plan-document"},
            {"id": 3, "name": "Cross-Reference Analysis",          "endpoint": "POST /api/contracts/cross-reference"},
            {"id": 4, "name": "Disclosure Analyzer",               "endpoint": "POST /api/disclosure/analyze"},
            {"id": 5, "name": "Audit Request Generator",           "endpoint": "POST /api/audit/generate"},
            {"id": 6, "name": "Compliance Deadline Tracker",       "endpoint": "GET /api/compliance/deadlines"},
            {"id": 7, "name": "SPC Parser",                        "endpoint": "POST /api/spc/parse"},
        ],
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Aggregate stats for the dashboard."""
    from services.db_service import _get_conn

    contracts_count = 0
    try:
        conn = _get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM contract_analyses").fetchone()
        contracts_count = row[0] if row else 0
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "claims_loaded": False,
        "claims_count": 0,
        "contracts_parsed": contracts_count,
        "modules_active": 7,
        "data_source": "contract_reader",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

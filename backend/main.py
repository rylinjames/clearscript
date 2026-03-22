"""
ClearScript — PBM Disclosure Audit Engine
FastAPI backend with 10 feature modules for pharmacy benefit manager transparency.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    contracts,
    disclosure,
    reports,
    rebates,
    spread,
    audit,
    network,
    formulary,
    benchmarks,
    compliance,
    claims_upload,
)

app = FastAPI(
    title="ClearScript — PBM Disclosure Audit Engine",
    description="AI-powered PBM contract analysis, disclosure auditing, spread pricing detection, rebate tracking, and compliance monitoring for employer health plan sponsors.",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(contracts.router)
app.include_router(disclosure.router)
app.include_router(reports.router)
app.include_router(rebates.router)
app.include_router(spread.router)
app.include_router(audit.router)
app.include_router(network.router)
app.include_router(formulary.router)
app.include_router(benchmarks.router)
app.include_router(compliance.router)
app.include_router(claims_upload.router)


@app.get("/")
async def root():
    return {
        "name": "ClearScript — PBM Disclosure Audit Engine",
        "version": "1.0.0",
        "features": [
            {"id": 1, "name": "Contract Intake & Parsing",        "endpoint": "POST /api/contracts/upload"},
            {"id": 2, "name": "Initial Disclosure Analyzer",      "endpoint": "POST /api/disclosure/analyze"},
            {"id": 3, "name": "Semiannual Report Auditor",        "endpoint": "GET /api/reports/audit"},
            {"id": 4, "name": "Rebate Passthrough Tracker",       "endpoint": "GET /api/rebates/analysis"},
            {"id": 5, "name": "Spread Pricing Detection",         "endpoint": "GET /api/spread/analysis"},
            {"id": 6, "name": "Audit Request Generator",          "endpoint": "POST /api/audit/generate"},
            {"id": 7, "name": "Pharmacy Network Adequacy",        "endpoint": "POST /api/network/analyze"},
            {"id": 8, "name": "Formulary Manipulation Detector",  "endpoint": "GET /api/formulary/analysis"},
            {"id": 9, "name": "Benchmarking Dashboard",           "endpoint": "GET /api/benchmarks/data"},
            {"id": 10,"name": "Compliance Deadline Tracker",      "endpoint": "GET /api/compliance/deadlines"},
        ],
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

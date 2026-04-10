"""Feature 9: Benchmarking Dashboard"""

from fastapi import APIRouter
from services.data_service import generate_benchmarks
from services.ndc_service import STATE_BENCHMARKS

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.get("/data")
async def benchmark_data():
    """
    Returns peer comparison data. Requires uploaded claims to compute
    plan-specific metrics against peer benchmarks.
    """
    from services.data_service import get_claims_status
    status = get_claims_status()
    if not status.get("custom_data_loaded"):
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to see peer benchmarks.",
            "benchmarks": None,
        }
    result = generate_benchmarks()

    return {
        "status": "success",
        "benchmarks": result,
    }


@router.get("/public-data")
async def public_benchmark_data():
    """
    Returns public benchmarking data from government and industry sources.
    Includes HHS OIG reports, state NDC compliance benchmarks, and
    net effective rebate ranges from large-book analysis.
    """
    return {
        "status": "success",
        "public_benchmarks": {
            "hhs_oig_report": {
                "source": "HHS Office of Inspector General",
                "work_plan_id": "w-00-24-31400",
                "title": "Collection of Rebates on Physician-Administered Drugs",
                "key_findings": [
                    "Approximately 40% of rebates that should have been collected were not — due to lack of enforcement and follow-up",
                    "Physician-administered drugs billed under J-codes frequently lack NDC crosswalks, preventing rebate collection",
                    "PBMs and plan sponsors often accept flat-rate rebate floors (e.g., 5%) instead of pursuing NDC-level rebates",
                ],
                "state_medicaid_rebate_collection": {
                    "top_performers": "States with single dominant payer (e.g., AL) achieve 95-98% collection",
                    "bottom_performers": "Fragmented markets collect as low as 38-50%",
                    "national_average_collection_rate": 0.60,
                    "gap_explanation": "The 40% uncollected figure represents billions in rebates that flow to PBMs or are simply never claimed",
                },
            },
            "state_ndc_compliance": {
                "source": "State NDC Compliance Benchmarks (ClearScript analysis of public filings)",
                "benchmarks": STATE_BENCHMARKS,
                "highlights": {
                    "best_in_class": {
                        "state": "Alabama",
                        "ndc_capture_rate": 0.98,
                        "enforcer": "BCBS Alabama",
                        "notes": "Effective monopoly enables strict enforcement — proof that near-100% capture is achievable",
                    },
                    "national_average": {
                        "ndc_capture_rate": 0.55,
                        "notes": "Most states capture barely half of available NDC-level rebates",
                    },
                    "gap_to_best": "43 percentage points between national average (55%) and Alabama benchmark (98%)",
                },
            },
            "net_effective_rebate_ranges": {
                "source": "Large-book analysis (24 states, millions of covered lives)",
                "weighted_net_effective_rebate": 0.24,
                "rebate_by_therapy_class": {
                    "range_low": 0.18,
                    "range_high": 0.31,
                    "notes": "Net effective rebate varies by therapy class from 18% to 31%",
                    "examples": [
                        {"class": "Diabetes (GLP-1)", "typical_range": "25-31%"},
                        {"class": "Oncology", "typical_range": "12-18%"},
                        {"class": "Immunology (TNF)", "typical_range": "22-28%"},
                        {"class": "Cardiovascular", "typical_range": "20-26%"},
                        {"class": "Respiratory", "typical_range": "18-24%"},
                    ],
                },
                "jcode_eligible_items": {
                    "accepted_floor": 0.05,
                    "notes": "Industry accepts a 5% rebate floor for J-code items — this is artificially low. With proper NDC crosswalks, actual rebates range 15-60% depending on drug.",
                    "gap_explanation": "PBMs benefit from the 5% floor because they avoid the operational cost of NDC-level billing enforcement while collecting higher rebates from manufacturers",
                },
            },
        },
    }

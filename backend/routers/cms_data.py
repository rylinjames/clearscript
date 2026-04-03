"""CMS Data Router — Unified access to 11+ CMS datasets."""

import logging
from fastapi import APIRouter, Query
from services.cms_data_service import (
    get_state_drug_trends,
    get_medicaid_drug_spending,
    get_partb_discarded_units,
    get_prescriber_patterns,
    get_provider_utilization,
    get_hcpcs_national_stats,
    get_opioid_patterns,
    get_inventory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cms-data", tags=["cms-data"])


@router.get("/state-trends")
async def state_trends(
    state: str = Query(..., description="Two-letter state abbreviation (e.g. CA, TX, NY)"),
    ndc: str = Query(default=None, description="Optional NDC code to filter by"),
):
    """
    State drug utilization trends across 2023-2025.
    Shows year-over-year prescriptions, reimbursement, and units for a given state.
    """
    return {
        "status": "success",
        "data": get_state_drug_trends(state=state, ndc=ndc),
    }


@router.get("/medicaid-spending")
async def medicaid_spending(
    drug: str = Query(default=None, description="Drug name to search (case-insensitive substring)"),
):
    """
    Medicaid drug spending lookup. Search by drug name to get brand/generic info,
    manufacturer, total spending by year (2019-2023), and total claims.
    """
    results = get_medicaid_drug_spending(drug_name=drug)
    return {
        "status": "success",
        "count": len(results),
        "data": results,
    }


@router.get("/discarded-units")
async def discarded_units(
    hcpcs: str = Query(default=None, description="HCPCS code to look up (or omit for all)"),
):
    """
    Part B discarded drug units. Shows discarded vs administered units per HCPCS code.
    Useful for identifying drugs where PBMs bill for full vials but significant amounts are wasted.
    """
    results = get_partb_discarded_units(hcpcs=hcpcs)
    return {
        "status": "success",
        "count": len(results),
        "data": results,
    }


@router.get("/prescriber-patterns")
async def prescriber_patterns(
    drug: str = Query(default=None, description="Drug name to filter by"),
    state: str = Query(default=None, description="State to filter by"),
):
    """
    Part D prescribing patterns by region and drug. Returns total prescribers,
    total claims, average claims per prescriber, and top prescribing regions.
    """
    return {
        "status": "success",
        "data": get_prescriber_patterns(drug_name=drug, state=state),
    }


@router.get("/provider")
async def provider_utilization(
    npi: str = Query(default=None, description="NPI number to look up"),
    specialty: str = Query(default=None, description="Specialty to search (substring)"),
    hcpcs: str = Query(default=None, description="HCPCS code (note: provider-level data has totals only)"),
):
    """
    Physician provider utilization lookup. Search by NPI or specialty.
    Returns provider name, specialty, total services, total beneficiaries, avg payment.
    """
    results = get_provider_utilization(npi=npi, specialty=specialty, hcpcs=hcpcs)
    return {
        "status": "success",
        "count": len(results),
        "data": results,
    }


@router.get("/hcpcs-stats")
async def hcpcs_stats(
    code: str = Query(..., description="HCPCS code to look up"),
):
    """
    National HCPCS statistics from the Physician/Supplier Procedure Summary.
    Returns total services, total payments, avg payment per service nationally.
    Powers the provider anomaly module with real national benchmarks.
    """
    return {
        "status": "success",
        "data": get_hcpcs_national_stats(hcpcs=code),
    }


@router.get("/opioid-patterns")
async def opioid_patterns(
    state: str = Query(default=None, description="State to filter by (or omit for all states)"),
):
    """
    Opioid prescribing data combining Medicare Part D and Medicaid sources.
    Returns prescribing rates by state with national averages for comparison.
    """
    return {
        "status": "success",
        "data": get_opioid_patterns(state=state),
    }


@router.get("/inventory")
async def inventory():
    """
    List all available CMS datasets with row counts, file sizes, and descriptions.
    """
    datasets = get_inventory()
    total_rows = sum(d["row_count"] for d in datasets)
    available = sum(1 for d in datasets if d["available"])
    return {
        "status": "success",
        "total_datasets": len(datasets),
        "available_datasets": available,
        "total_rows": total_rows,
        "datasets": datasets,
    }

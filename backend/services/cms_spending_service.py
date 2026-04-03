"""
CMS Drug Spending Service.

Loads and queries CMS Medicare Part B and Part D drug spending datasets.
Provides real Medicare spending benchmarks for the NDC/J-code module,
drug lookup enrichment, and plan cost benchmarking.
"""

import csv
import logging
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger("clearscript.cms_spending_service")

# ---------------------------------------------------------------------------
# Module-level caches (lazy-loaded)
# ---------------------------------------------------------------------------

_partb_data: Optional[List[Dict[str, Any]]] = None
_partd_data: Optional[List[Dict[str, Any]]] = None
_partb_quarterly_data: Optional[List[Dict[str, Any]]] = None

# Index caches
_partb_jcode_index: Optional[Dict[str, Dict[str, Any]]] = None
_partd_brand_index: Optional[Dict[str, List[Dict[str, Any]]]] = None
_partd_generic_index: Optional[Dict[str, List[Dict[str, Any]]]] = None

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cms")


def _safe_float(value: str) -> Optional[float]:
    """Convert a string to float, returning None for empty or non-numeric values."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value.replace(",", ""))
    except (ValueError, TypeError):
        return None


def _safe_int(value: str) -> Optional[int]:
    """Convert a string to int, returning None for empty or non-numeric values."""
    f = _safe_float(value)
    if f is None:
        return None
    return int(f)


def _read_csv(filename: str) -> List[Dict[str, str]]:
    """Read a CSV file and return list of row dicts."""
    filepath = os.path.join(_DATA_DIR, filename)
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        logger.info("Loaded %d rows from %s", len(rows), filename)
    except FileNotFoundError:
        logger.error("CMS data file not found: %s", filepath)
    except Exception as e:
        logger.error("Error reading %s: %s", filepath, e)
    return rows


# ---------------------------------------------------------------------------
# Part B spending
# ---------------------------------------------------------------------------

def load_partb_spending() -> List[Dict[str, Any]]:
    """
    Lazy-load Part B drug spending CSV.

    Returns list of dicts with normalized fields for each HCPCS drug code.
    Uses 2023 as the most recent year and computes year-over-year change
    from 2022 to 2023.
    """
    global _partb_data, _partb_jcode_index

    if _partb_data is not None:
        return _partb_data

    raw_rows = _read_csv("partb_drug_spending.csv")
    _partb_data = []
    _partb_jcode_index = {}

    for row in raw_rows:
        tot_spending_2023 = _safe_float(row.get("Tot_Spndng_2023", ""))
        tot_spending_2022 = _safe_float(row.get("Tot_Spndng_2022", ""))
        tot_claims_2023 = _safe_int(row.get("Tot_Clms_2023", ""))
        avg_cost_per_claim = _safe_float(row.get("Avg_Spndng_Per_Clm_2023", ""))
        tot_benes = _safe_int(row.get("Tot_Benes_2023", ""))

        # Year-over-year change
        yoy_change = None
        if tot_spending_2023 is not None and tot_spending_2022 is not None and tot_spending_2022 > 0:
            yoy_change = round((tot_spending_2023 - tot_spending_2022) / tot_spending_2022, 4)

        entry = {
            "hcpcs_code": row.get("HCPCS_Cd", "").strip(),
            "description": row.get("HCPCS_Desc", "").strip(),
            "brand_name": row.get("Brnd_Name", "").strip(),
            "generic_name": row.get("Gnrc_Name", "").strip(),
            "total_spending": tot_spending_2023,
            "total_spending_2022": tot_spending_2022,
            "total_claims": tot_claims_2023,
            "total_beneficiaries": tot_benes,
            "avg_cost_per_claim": avg_cost_per_claim,
            "avg_cost_per_dosage_unit": _safe_float(row.get("Avg_Spndng_Per_Dsg_Unt_2023", "")),
            "year_over_year_change": yoy_change,
            "cagr_2019_2023": _safe_float(row.get("CAGR_Avg_Spnd_Per_Dsg_Unt_19_23", "")),
        }

        _partb_data.append(entry)

        # Index by HCPCS code (J-code)
        code = entry["hcpcs_code"].upper()
        if code:
            _partb_jcode_index[code] = entry

    return _partb_data


# ---------------------------------------------------------------------------
# Part D spending
# ---------------------------------------------------------------------------

def load_partd_spending() -> List[Dict[str, Any]]:
    """
    Lazy-load Part D drug spending CSV.

    Returns list of dicts with normalized fields. Filters to 'Overall'
    manufacturer rows to avoid double-counting when a drug has multiple
    manufacturers listed individually.
    """
    global _partd_data, _partd_brand_index, _partd_generic_index

    if _partd_data is not None:
        return _partd_data

    raw_rows = _read_csv("partd_drug_spending.csv")
    _partd_data = []
    _partd_brand_index = {}
    _partd_generic_index = {}

    for row in raw_rows:
        mftr_name = row.get("Mftr_Name", "").strip()

        tot_spending = _safe_float(row.get("Tot_Spndng_2023", ""))
        tot_claims = _safe_int(row.get("Tot_Clms_2023", ""))
        tot_benes = _safe_int(row.get("Tot_Benes_2023", ""))
        avg_cost_per_claim = _safe_float(row.get("Avg_Spnd_Per_Clm_2023", ""))

        entry = {
            "brand_name": row.get("Brnd_Name", "").strip(),
            "generic_name": row.get("Gnrc_Name", "").strip(),
            "manufacturer": mftr_name,
            "total_manufacturers": _safe_int(row.get("Tot_Mftr", "")),
            "total_spending": tot_spending,
            "total_claims": tot_claims,
            "total_beneficiaries": tot_benes,
            "avg_cost_per_claim": avg_cost_per_claim,
            "avg_cost_per_dosage_unit": _safe_float(row.get("Avg_Spnd_Per_Dsg_Unt_Wghtd_2023", "")),
            "yoy_change_per_unit": _safe_float(row.get("Chg_Avg_Spnd_Per_Dsg_Unt_22_23", "")),
            "cagr_2019_2023": _safe_float(row.get("CAGR_Avg_Spnd_Per_Dsg_Unt_19_23", "")),
            "is_overall": mftr_name.lower() == "overall",
        }

        _partd_data.append(entry)

        # Index by brand and generic name (lowered)
        brand_key = entry["brand_name"].lower()
        generic_key = entry["generic_name"].lower()
        if brand_key:
            _partd_brand_index.setdefault(brand_key, []).append(entry)
        if generic_key:
            _partd_generic_index.setdefault(generic_key, []).append(entry)

    return _partd_data


# ---------------------------------------------------------------------------
# Part B quarterly spending
# ---------------------------------------------------------------------------

def load_partb_quarterly() -> List[Dict[str, Any]]:
    """Lazy-load Part B quarterly spending CSV."""
    global _partb_quarterly_data

    if _partb_quarterly_data is not None:
        return _partb_quarterly_data

    raw_rows = _read_csv("partb_quarterly_spending.csv")
    _partb_quarterly_data = []

    for row in raw_rows:
        entry = {
            "brand_name": row.get("Brnd_Name", "").strip(),
            "generic_name": row.get("Gnrc_Name", "").strip(),
            "hcpcs_code": row.get("HCPCS_Cd", "").strip(),
            "hcpcs_desc": row.get("HCPCS_Desc", "").strip(),
            "year": row.get("Year", "").strip(),
            "total_beneficiaries": _safe_int(row.get("Tot_Benes", "")),
            "total_claims": _safe_int(row.get("Tot_Clms", "")),
            "total_spending": _safe_float(row.get("Tot_Spndng", "")),
            "avg_spend_per_bene": _safe_float(row.get("Avg_Spnd_Per_Bene", "")),
            "avg_spend_per_claim": _safe_float(row.get("Avg_Spnd_Per_Clm", "")),
        }
        _partb_quarterly_data.append(entry)

    return _partb_quarterly_data


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

def get_jcode_spending(jcode: str) -> Dict[str, Any]:
    """
    Look up a specific J-code (or any HCPCS code) in Part B spending data.

    Returns spending details including total Medicare spending, claims,
    average cost per claim, and year-over-year change. This powers the
    NDC/J-code module with real dollar amounts.
    """
    load_partb_spending()

    code = jcode.strip().upper()
    entry = _partb_jcode_index.get(code)

    if entry is None:
        return {"found": False, "hcpcs_code": code, "error": "J-code not found in CMS Part B spending data"}

    return {
        "found": True,
        "hcpcs_code": entry["hcpcs_code"],
        "description": entry["description"],
        "brand_name": entry["brand_name"],
        "generic_name": entry["generic_name"],
        "medicare_total_spending": entry["total_spending"],
        "medicare_total_claims": entry["total_claims"],
        "medicare_total_beneficiaries": entry["total_beneficiaries"],
        "medicare_avg_cost_per_claim": entry["avg_cost_per_claim"],
        "medicare_avg_cost_per_dosage_unit": entry["avg_cost_per_dosage_unit"],
        "year_over_year_change": entry["year_over_year_change"],
        "cagr_2019_2023": entry["cagr_2019_2023"],
        "data_source": "CMS Medicare Part B Drug Spending Dashboard (2023)",
    }


def get_drug_spending(drug_name: str) -> Dict[str, Any]:
    """
    Search Part D spending data by drug name (case-insensitive substring).

    Searches brand name first, then generic name. Returns the 'Overall'
    manufacturer row when available for aggregate figures.
    """
    load_partd_spending()

    query = drug_name.strip().lower()
    if not query:
        return {"found": False, "error": "Empty drug name"}

    # Try exact brand match first
    matches = _partd_brand_index.get(query, [])

    # Try exact generic match
    if not matches:
        matches = _partd_generic_index.get(query, [])

    # Substring search across brand and generic names
    if not matches:
        for entry in _partd_data:
            if query in entry["brand_name"].lower() or query in entry["generic_name"].lower():
                matches.append(entry)

    if not matches:
        return {"found": False, "drug_name": drug_name, "error": "Drug not found in CMS Part D spending data"}

    # Prefer the 'Overall' row for aggregate stats
    overall = [m for m in matches if m.get("is_overall")]
    best = overall[0] if overall else matches[0]

    return {
        "found": True,
        "brand_name": best["brand_name"],
        "generic_name": best["generic_name"],
        "manufacturer": best["manufacturer"],
        "medicare_total_spending": best["total_spending"],
        "medicare_total_claims": best["total_claims"],
        "medicare_total_beneficiaries": best["total_beneficiaries"],
        "medicare_avg_cost_per_claim": best["avg_cost_per_claim"],
        "medicare_avg_cost_per_dosage_unit": best["avg_cost_per_dosage_unit"],
        "yoy_change_per_unit": best["yoy_change_per_unit"],
        "cagr_2019_2023": best["cagr_2019_2023"],
        "total_matches": len(matches),
        "data_source": "CMS Medicare Part D Drug Spending Dashboard (2023)",
    }


def get_top_drugs(n: int = 25, sort_by: str = "spending") -> List[Dict[str, Any]]:
    """
    Return top N drugs by spending or claims from Part D data.

    Args:
        n: Number of results to return (default 25).
        sort_by: 'spending' or 'claims'.

    Only includes 'Overall' manufacturer rows to avoid duplicates.
    """
    load_partd_spending()

    # Filter to Overall rows only for de-duplication
    overall_rows = [d for d in _partd_data if d.get("is_overall")]

    if sort_by == "claims":
        sort_key = "total_claims"
    else:
        sort_key = "total_spending"

    # Sort descending, treating None as 0
    sorted_rows = sorted(
        overall_rows,
        key=lambda d: d.get(sort_key) or 0,
        reverse=True,
    )

    results = []
    for entry in sorted_rows[:n]:
        results.append({
            "rank": len(results) + 1,
            "brand_name": entry["brand_name"],
            "generic_name": entry["generic_name"],
            "manufacturer": entry["manufacturer"],
            "total_spending": entry["total_spending"],
            "total_claims": entry["total_claims"],
            "total_beneficiaries": entry["total_beneficiaries"],
            "avg_cost_per_claim": entry["avg_cost_per_claim"],
        })

    return results


def benchmark_drug_cost(drug_name: str, plan_cost: float) -> Dict[str, Any]:
    """
    Compare a plan's cost per claim for a drug against the Medicare
    national average from Part D data.

    Returns the plan cost, Medicare average, absolute difference,
    percentage difference, and a rough percentile estimate.
    """
    spending = get_drug_spending(drug_name)

    if not spending.get("found"):
        return {
            "found": False,
            "drug_name": drug_name,
            "plan_cost": plan_cost,
            "error": f"Drug '{drug_name}' not found in CMS spending data for benchmarking",
        }

    medicare_avg = spending["medicare_avg_cost_per_claim"]
    if medicare_avg is None or medicare_avg == 0:
        return {
            "found": False,
            "drug_name": drug_name,
            "plan_cost": plan_cost,
            "error": "Medicare average cost data unavailable for this drug",
        }

    difference = round(plan_cost - medicare_avg, 2)
    pct_difference = round(difference / medicare_avg * 100, 1)

    # Rough percentile estimate based on how far from Medicare average
    # Assumes roughly normal distribution around the Medicare mean
    if pct_difference <= -30:
        percentile_estimate = "< 10th percentile (well below Medicare average)"
    elif pct_difference <= -15:
        percentile_estimate = "10th-25th percentile (below Medicare average)"
    elif pct_difference <= -5:
        percentile_estimate = "25th-40th percentile (slightly below Medicare average)"
    elif pct_difference <= 5:
        percentile_estimate = "40th-60th percentile (near Medicare average)"
    elif pct_difference <= 15:
        percentile_estimate = "60th-75th percentile (slightly above Medicare average)"
    elif pct_difference <= 30:
        percentile_estimate = "75th-90th percentile (above Medicare average)"
    else:
        percentile_estimate = "> 90th percentile (well above Medicare average)"

    return {
        "found": True,
        "drug_name": drug_name,
        "brand_name": spending["brand_name"],
        "generic_name": spending["generic_name"],
        "plan_cost_per_claim": plan_cost,
        "medicare_avg_cost_per_claim": medicare_avg,
        "difference": difference,
        "pct_difference": pct_difference,
        "percentile_estimate": percentile_estimate,
        "data_source": spending["data_source"],
    }


# ---------------------------------------------------------------------------
# Aggregate statistics (used by cms_partd_service for real benchmarks)
# ---------------------------------------------------------------------------

def get_partd_aggregate_stats() -> Dict[str, Any]:
    """
    Compute aggregate statistics from Part D spending data for use
    in benchmark reports.
    """
    load_partd_spending()

    overall_rows = [d for d in _partd_data if d.get("is_overall")]

    total_spend = sum(d["total_spending"] for d in overall_rows if d["total_spending"] is not None)
    total_claims = sum(d["total_claims"] for d in overall_rows if d["total_claims"] is not None)
    total_benes = sum(d["total_beneficiaries"] for d in overall_rows if d["total_beneficiaries"] is not None)
    drug_count = len(overall_rows)

    # Average cost per claim across all drugs
    avg_cost_per_claim = round(total_spend / total_claims, 2) if total_claims > 0 else 0

    # Top 10 by spending
    top_10 = get_top_drugs(n=10, sort_by="spending")

    # Spending concentration
    top_10_spend = sum(d["total_spending"] or 0 for d in top_10)
    concentration_pct = round(top_10_spend / total_spend * 100, 1) if total_spend > 0 else 0

    # Year-over-year changes
    yoy_values = [d["yoy_change_per_unit"] for d in overall_rows if d["yoy_change_per_unit"] is not None]
    avg_yoy = round(sum(yoy_values) / len(yoy_values), 4) if yoy_values else None

    return {
        "total_drugs_tracked": drug_count,
        "total_spending_2023": round(total_spend, 2),
        "total_claims_2023": total_claims,
        "total_beneficiaries_2023": total_benes,
        "avg_cost_per_claim": avg_cost_per_claim,
        "top_10_drugs_by_spending": top_10,
        "top_10_spending_concentration_pct": concentration_pct,
        "avg_yoy_cost_change_per_unit": avg_yoy,
        "data_source": "CMS Medicare Part D Drug Spending Dashboard (2023)",
    }

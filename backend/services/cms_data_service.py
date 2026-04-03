"""
Unified CMS Data Access Layer.
Provides lazy-loaded, memory-efficient access to 11 CMS datasets:
  - State Drug Utilization (2023, 2024, 2025)
  - Medicaid Spending by Drug
  - Part B Discarded Units
  - Part D Prescriber Patterns (geographic + drug)
  - Part D Prescribers by Provider
  - Part D Opioid Geographic
  - Medicaid Opioid Geographic
  - Physician by Provider
  - Physician Geographic Service
  - Physician/Supplier Procedure Summary

All data loaded from local CSVs using stdlib csv module only (no pandas).
Large files are aggregated/indexed on load to minimize memory usage.
"""

import csv
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "cms")
)

# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------

# State drug utilization: {year: {state: [rows]}}
_state_drug_cache: Dict[int, Dict[str, list]] = {}

# Medicaid spending by drug: list of row dicts (17K rows — fine in memory)
_medicaid_spending: Optional[List[dict]] = None

# Part B discarded units: list of row dicts (825 rows — tiny)
_partb_discarded: Optional[List[dict]] = None

# Part D prescriber geo+drug: {(drug_lower, state_upper): aggregated_dict}
_prescriber_geo_drug: Optional[Dict[str, list]] = None

# Part D prescribers by provider: {npi: summary_dict}
_prescriber_by_provider: Optional[Dict[str, dict]] = None

# Opioid data: {state: {medicare: {...}, medicaid: {...}}}
_opioid_by_state: Optional[Dict[str, dict]] = None

# Physician by provider: {npi: summary_dict}
_physician_by_provider: Optional[Dict[str, dict]] = None

# Physician geo service: loaded on demand and cached
_physician_geo_service: Optional[List[dict]] = None

# Physician/supplier procedure summary: {hcpcs: aggregated_stats}
_hcpcs_national: Optional[Dict[str, dict]] = None

# Dataset inventory metadata
_inventory_cache: Optional[list] = None


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning default on failure."""
    if val is None:
        return default
    try:
        s = str(val).strip().replace(",", "")
        if s == "" or s.lower() in ("", "nan", "n/a", "null"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Convert a value to int, returning default on failure."""
    return int(_safe_float(val, float(default)))


def _csv_path(filename: str) -> str:
    return os.path.join(_DATA_DIR, filename)


def _file_exists(filename: str) -> bool:
    return os.path.exists(_csv_path(filename))


def _count_rows(filename: str) -> int:
    """Count rows in a CSV (excluding header). Used for inventory."""
    path = _csv_path(filename)
    if not os.path.exists(path):
        return 0
    count = 0
    with open(path, "r", encoding="utf-8") as fh:
        next(fh, None)  # skip header
        for _ in fh:
            count += 1
    return count


# ---------------------------------------------------------------------------
# 1. State Drug Utilization Trends (2023 / 2024 / 2025)
# ---------------------------------------------------------------------------

_STATE_DRUG_FILES = {
    2023: "state_drug_utilization_2023.csv",
    2024: "state_drug_utilization_2024.csv",
    2025: "state_drug_utilization_2025.csv",
}


def _load_state_drug_year(year: int, state: str) -> list:
    """Load rows for a specific state from one year file. Cache per year+state."""
    if year not in _state_drug_cache:
        _state_drug_cache[year] = {}
    if state in _state_drug_cache[year]:
        return _state_drug_cache[year][state]

    fname = _STATE_DRUG_FILES.get(year)
    if not fname or not _file_exists(fname):
        logger.warning("State drug utilization file not found for year %d", year)
        _state_drug_cache[year][state] = []
        return []

    path = _csv_path(fname)
    rows = []
    state_upper = state.upper()
    logger.info("Loading state drug utilization %d for state=%s from %s", year, state_upper, fname)

    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if (row.get("State") or "").upper() == state_upper:
                rows.append(row)

    _state_drug_cache[year][state_upper] = rows
    logger.info("Loaded %d rows for %s/%d", len(rows), state_upper, year)
    return rows


def get_state_drug_trends(state: str, ndc: str = None) -> dict:
    """
    Load 2023/2024/2025 state drug utilization CSVs for a given state.
    Optionally filter by NDC. Returns year-over-year trend: prescriptions,
    amount reimbursed, units reimbursed, showing 3-year trajectory.
    """
    if not state:
        return {"error": "state parameter is required"}

    state_upper = state.upper()
    yearly_data = {}

    for year in (2023, 2024, 2025):
        rows = _load_state_drug_year(year, state_upper)
        if ndc:
            rows = [r for r in rows if (r.get("NDC") or "").strip() == ndc.strip()]

        total_prescriptions = sum(_safe_int(r.get("Number of Prescriptions")) for r in rows)
        total_reimbursed = sum(_safe_float(r.get("Total Amount Reimbursed")) for r in rows)
        total_units = sum(_safe_float(r.get("Units Reimbursed")) for r in rows)
        medicaid_reimbursed = sum(_safe_float(r.get("Medicaid Amount Reimbursed")) for r in rows)
        drug_count = len(set((r.get("NDC") or "") for r in rows if r.get("NDC")))

        yearly_data[year] = {
            "year": year,
            "total_prescriptions": total_prescriptions,
            "total_amount_reimbursed": round(total_reimbursed, 2),
            "total_units_reimbursed": round(total_units, 2),
            "medicaid_amount_reimbursed": round(medicaid_reimbursed, 2),
            "unique_ndcs": drug_count,
            "row_count": len(rows),
        }

    # Compute YoY changes
    years_list = [2023, 2024, 2025]
    trends = []
    for i in range(1, len(years_list)):
        prev_year = years_list[i - 1]
        curr_year = years_list[i]
        prev = yearly_data[prev_year]
        curr = yearly_data[curr_year]

        def _pct_change(curr_val, prev_val):
            if prev_val == 0:
                return None
            return round((curr_val - prev_val) / prev_val * 100, 2)

        trends.append({
            "period": f"{prev_year}-{curr_year}",
            "prescriptions_change_pct": _pct_change(curr["total_prescriptions"], prev["total_prescriptions"]),
            "reimbursement_change_pct": _pct_change(curr["total_amount_reimbursed"], prev["total_amount_reimbursed"]),
            "units_change_pct": _pct_change(curr["total_units_reimbursed"], prev["total_units_reimbursed"]),
        })

    return {
        "state": state_upper,
        "ndc_filter": ndc,
        "yearly_data": yearly_data,
        "trends": trends,
        "data_source": "CMS State Drug Utilization Data (2023-2025)",
    }


# ---------------------------------------------------------------------------
# 2. Medicaid Spending by Drug
# ---------------------------------------------------------------------------

def _ensure_medicaid_spending() -> List[dict]:
    global _medicaid_spending
    if _medicaid_spending is not None:
        return _medicaid_spending

    fname = "medicaid_spending_by_drug.csv"
    if not _file_exists(fname):
        logger.warning("Medicaid spending file not found: %s", fname)
        _medicaid_spending = []
        return _medicaid_spending

    logger.info("Loading medicaid_spending_by_drug.csv ...")
    _medicaid_spending = []
    with open(_csv_path(fname), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            _medicaid_spending.append(row)

    logger.info("Loaded %d medicaid spending rows", len(_medicaid_spending))
    return _medicaid_spending


def get_medicaid_drug_spending(drug_name: str = None) -> list:
    """
    Search medicaid_spending_by_drug.csv by drug name (case-insensitive substring).
    Returns brand/generic name, manufacturer, total spending by year, total claims.
    """
    data = _ensure_medicaid_spending()

    if drug_name:
        needle = drug_name.lower()
        data = [
            r for r in data
            if needle in (r.get("Brnd_Name") or "").lower()
            or needle in (r.get("Gnrc_Name") or "").lower()
        ]

    results = []
    for row in data[:200]:  # limit to 200 results
        spending_by_year = {}
        for year in range(2019, 2024):
            spending_key = f"Tot_Spndng_{year}"
            claims_key = f"Tot_Clms_{year}"
            units_key = f"Tot_Dsg_Unts_{year}"
            if spending_key in row:
                spending_by_year[year] = {
                    "total_spending": _safe_float(row.get(spending_key)),
                    "total_claims": _safe_int(row.get(claims_key)),
                    "total_dosage_units": _safe_float(row.get(units_key)),
                    "avg_spend_per_unit": _safe_float(row.get(f"Avg_Spnd_Per_Dsg_Unt_Wghtd_{year}")),
                    "avg_spend_per_claim": _safe_float(row.get(f"Avg_Spnd_Per_Clm_{year}")),
                }

        results.append({
            "brand_name": (row.get("Brnd_Name") or "").strip(),
            "generic_name": (row.get("Gnrc_Name") or "").strip(),
            "total_manufacturers": _safe_int(row.get("Tot_Mftr")),
            "manufacturer": (row.get("Mftr_Name") or "").strip(),
            "spending_by_year": spending_by_year,
            "yoy_change_avg_spend_per_unit": _safe_float(row.get("Chg_Avg_Spnd_Per_Dsg_Unt_22_23")),
            "cagr_avg_spend_per_unit_2019_2023": _safe_float(row.get("CAGR_Avg_Spnd_Per_Dsg_Unt_19_23")),
        })

    return results


# ---------------------------------------------------------------------------
# 3. Part B Discarded Units
# ---------------------------------------------------------------------------

def _ensure_partb_discarded() -> List[dict]:
    global _partb_discarded
    if _partb_discarded is not None:
        return _partb_discarded

    fname = "partb_discarded_units.csv"
    if not _file_exists(fname):
        logger.warning("Part B discarded units file not found: %s", fname)
        _partb_discarded = []
        return _partb_discarded

    logger.info("Loading partb_discarded_units.csv ...")
    _partb_discarded = []
    with open(_csv_path(fname), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            _partb_discarded.append(row)

    logger.info("Loaded %d Part B discarded unit rows", len(_partb_discarded))
    return _partb_discarded


def get_partb_discarded_units(hcpcs: str = None) -> list:
    """
    For a given HCPCS code (or all), return discarded units, total units,
    waste percentage. Useful for identifying drugs where PBMs bill for full
    vials but significant amounts are wasted.
    """
    data = _ensure_partb_discarded()

    if hcpcs:
        hcpcs_upper = hcpcs.upper()
        data = [r for r in data if (r.get("HCPCS_Cd") or "").upper() == hcpcs_upper]

    results = []
    for row in data:
        total_allowed = _safe_float(row.get("Tot_Mdcr_Alowd_Amt"))
        administered = _safe_float(row.get("Tot_Mdcr_Alowd_Admnrd_Amt"))
        discarded = _safe_float(row.get("Tot_Mdcr_Alowd_Dscrd_Amt"))
        pct_administered = _safe_float(row.get("PCT_Admnrd_Units"))
        pct_discarded = _safe_float(row.get("PCT_Dscrd_Units"))

        results.append({
            "hcpcs_code": (row.get("HCPCS_Cd") or "").strip(),
            "brand_name": (row.get("Brnd_Name") or "").strip(),
            "generic_name": (row.get("Gnrc_Name") or "").strip(),
            "total_medicare_allowed": round(total_allowed, 2),
            "administered_amount": round(administered, 2),
            "discarded_amount": round(discarded, 2),
            "pct_administered": round(pct_administered * 100, 2) if pct_administered <= 1 else round(pct_administered, 2),
            "pct_discarded": round(pct_discarded * 100, 2) if pct_discarded <= 1 else round(pct_discarded, 2),
            "waste_flag": pct_discarded > 0.05,  # flag if >5% waste
        })

    # Sort by discarded amount descending
    results.sort(key=lambda x: x["discarded_amount"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 4. Prescriber Patterns (Part D Geo + Drug)
# ---------------------------------------------------------------------------

def _ensure_prescriber_geo_drug() -> List[dict]:
    global _prescriber_geo_drug
    if _prescriber_geo_drug is not None:
        return _prescriber_geo_drug

    fname = "partd_prescribers_geo_drug.csv"
    if not _file_exists(fname):
        logger.warning("Prescriber geo drug file not found: %s", fname)
        _prescriber_geo_drug = []
        return _prescriber_geo_drug

    logger.info("Loading partd_prescribers_geo_drug.csv ...")
    _prescriber_geo_drug = []
    with open(_csv_path(fname), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            _prescriber_geo_drug.append(row)

    logger.info("Loaded %d prescriber geo-drug rows", len(_prescriber_geo_drug))
    return _prescriber_geo_drug


def get_prescriber_patterns(drug_name: str = None, state: str = None) -> dict:
    """
    For a drug and/or state, return: total prescribers, total claims,
    avg claims per prescriber, top prescribing regions.
    """
    data = _ensure_prescriber_geo_drug()

    filtered = data
    if drug_name:
        needle = drug_name.lower()
        filtered = [
            r for r in filtered
            if needle in (r.get("Brnd_Name") or "").lower()
            or needle in (r.get("Gnrc_Name") or "").lower()
        ]

    if state:
        state_upper = state.upper()
        filtered = [
            r for r in filtered
            if (r.get("Prscrbr_Geo_Desc") or "").upper() == state_upper
            or (r.get("Prscrbr_Geo_Cd") or "").upper() == state_upper
        ]

    total_prescribers = sum(_safe_int(r.get("Tot_Prscrbrs")) for r in filtered)
    total_claims = sum(_safe_int(r.get("Tot_Clms")) for r in filtered)
    total_30day_fills = sum(_safe_int(r.get("Tot_30day_Fills")) for r in filtered)
    total_drug_cost = sum(_safe_float(r.get("Tot_Drug_Cst")) for r in filtered)
    total_benes = sum(_safe_int(r.get("Tot_Benes")) for r in filtered)

    avg_claims_per_prescriber = round(total_claims / total_prescribers, 2) if total_prescribers > 0 else 0

    # Top prescribing regions
    region_agg: Dict[str, dict] = {}
    for r in filtered:
        region = (r.get("Prscrbr_Geo_Desc") or "Unknown").strip()
        if region not in region_agg:
            region_agg[region] = {"claims": 0, "prescribers": 0, "cost": 0.0}
        region_agg[region]["claims"] += _safe_int(r.get("Tot_Clms"))
        region_agg[region]["prescribers"] += _safe_int(r.get("Tot_Prscrbrs"))
        region_agg[region]["cost"] += _safe_float(r.get("Tot_Drug_Cst"))

    top_regions = sorted(region_agg.items(), key=lambda x: x[1]["claims"], reverse=True)[:20]

    # Opioid flag summary
    opioid_rows = [r for r in filtered if (r.get("Opioid_Drug_Flag") or "").upper() == "Y"]
    opioid_claims = sum(_safe_int(r.get("Tot_Clms")) for r in opioid_rows)

    return {
        "filters": {"drug_name": drug_name, "state": state},
        "total_prescribers": total_prescribers,
        "total_claims": total_claims,
        "total_30day_fills": total_30day_fills,
        "total_drug_cost": round(total_drug_cost, 2),
        "total_beneficiaries": total_benes,
        "avg_claims_per_prescriber": avg_claims_per_prescriber,
        "opioid_claims": opioid_claims,
        "matching_rows": len(filtered),
        "top_regions": [
            {
                "region": name,
                "claims": stats["claims"],
                "prescribers": stats["prescribers"],
                "cost": round(stats["cost"], 2),
            }
            for name, stats in top_regions
        ],
        "data_source": "CMS Part D Prescribers by Geography and Drug",
    }


# ---------------------------------------------------------------------------
# 5. Provider Utilization (Physician by Provider)
# ---------------------------------------------------------------------------

def _ensure_physician_by_provider() -> Dict[str, dict]:
    global _physician_by_provider
    if _physician_by_provider is not None:
        return _physician_by_provider

    fname = "physician_by_provider.csv"
    if not _file_exists(fname):
        logger.warning("Physician by provider file not found: %s", fname)
        _physician_by_provider = {}
        return _physician_by_provider

    logger.info("Loading physician_by_provider.csv (indexing by NPI) ...")
    _physician_by_provider = {}
    with open(_csv_path(fname), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = (row.get("Rndrng_NPI") or "").strip()
            if not npi:
                continue
            _physician_by_provider[npi] = {
                "npi": npi,
                "last_name": (row.get("Rndrng_Prvdr_Last_Org_Name") or "").strip(),
                "first_name": (row.get("Rndrng_Prvdr_First_Name") or "").strip(),
                "credentials": (row.get("Rndrng_Prvdr_Crdntls") or "").strip(),
                "entity_code": (row.get("Rndrng_Prvdr_Ent_Cd") or "").strip(),
                "city": (row.get("Rndrng_Prvdr_City") or "").strip(),
                "state": (row.get("Rndrng_Prvdr_State_Abrvtn") or "").strip(),
                "zip": (row.get("Rndrng_Prvdr_Zip5") or "").strip(),
                "specialty": (row.get("Rndrng_Prvdr_Type") or "").strip(),
                "participating": (row.get("Rndrng_Prvdr_Mdcr_Prtcptg_Ind") or "").strip(),
                "total_hcpcs_codes": _safe_int(row.get("Tot_HCPCS_Cds")),
                "total_beneficiaries": _safe_int(row.get("Tot_Benes")),
                "total_services": _safe_int(row.get("Tot_Srvcs")),
                "total_submitted_charges": _safe_float(row.get("Tot_Sbmtd_Chrg")),
                "total_medicare_allowed": _safe_float(row.get("Tot_Mdcr_Alowd_Amt")),
                "total_medicare_payment": _safe_float(row.get("Tot_Mdcr_Pymt_Amt")),
                "total_medicare_standardized": _safe_float(row.get("Tot_Mdcr_Stdzd_Amt")),
                "drug_total_services": _safe_int(row.get("Drug_Tot_Srvcs")),
                "drug_submitted_charges": _safe_float(row.get("Drug_Sbmtd_Chrg")),
                "drug_medicare_payment": _safe_float(row.get("Drug_Mdcr_Pymt_Amt")),
                "med_total_services": _safe_int(row.get("Med_Tot_Srvcs")),
                "med_submitted_charges": _safe_float(row.get("Med_Sbmtd_Chrg")),
                "med_medicare_payment": _safe_float(row.get("Med_Mdcr_Pymt_Amt")),
                "avg_beneficiary_age": _safe_float(row.get("Bene_Avg_Age")),
                "avg_risk_score": _safe_float(row.get("Bene_Avg_Risk_Scre")),
            }

    logger.info("Indexed %d providers by NPI", len(_physician_by_provider))
    return _physician_by_provider


def get_provider_utilization(npi: str = None, specialty: str = None, hcpcs: str = None) -> list:
    """
    Search physician_by_provider.csv by NPI, specialty, or HCPCS code.
    Return provider name, specialty, total services, total beneficiaries, avg payment.
    Note: HCPCS filtering is not available in the by-provider summary (it has totals only).
    For HCPCS-level data, use get_hcpcs_national_stats instead.
    """
    index = _ensure_physician_by_provider()

    if npi:
        npi = npi.strip()
        record = index.get(npi)
        if record:
            avg_payment = (
                round(record["total_medicare_payment"] / record["total_services"], 2)
                if record["total_services"] > 0 else 0
            )
            return [{**record, "avg_payment_per_service": avg_payment}]
        return []

    # For specialty search, iterate the index
    results = []
    if specialty:
        specialty_lower = specialty.lower()
        for rec in index.values():
            if specialty_lower in rec["specialty"].lower():
                avg_payment = (
                    round(rec["total_medicare_payment"] / rec["total_services"], 2)
                    if rec["total_services"] > 0 else 0
                )
                results.append({**rec, "avg_payment_per_service": avg_payment})
                if len(results) >= 100:
                    break

    if not npi and not specialty:
        # Return a sample
        count = 0
        for rec in index.values():
            avg_payment = (
                round(rec["total_medicare_payment"] / rec["total_services"], 2)
                if rec["total_services"] > 0 else 0
            )
            results.append({**rec, "avg_payment_per_service": avg_payment})
            count += 1
            if count >= 50:
                break

    return results


# ---------------------------------------------------------------------------
# 6. HCPCS National Stats (Physician/Supplier Procedure Summary)
# ---------------------------------------------------------------------------

def _ensure_hcpcs_national() -> Dict[str, dict]:
    """
    Aggregate physician_supplier_procedure_summary.csv (1.45M rows) by HCPCS code.
    Stores only per-code aggregated stats to minimize memory.
    """
    global _hcpcs_national
    if _hcpcs_national is not None:
        return _hcpcs_national

    fname = "physician_supplier_procedure_summary.csv"
    if not _file_exists(fname):
        logger.warning("Physician supplier procedure summary not found: %s", fname)
        _hcpcs_national = {}
        return _hcpcs_national

    logger.info("Loading physician_supplier_procedure_summary.csv (aggregating by HCPCS) ...")
    agg: Dict[str, dict] = {}
    row_count = 0

    with open(_csv_path(fname), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row_count += 1
            hcpcs = (row.get("HCPCS_CD") or "").strip().upper()
            if not hcpcs:
                continue

            services = _safe_float(row.get("PSPS_SUBMITTED_SERVICE_CNT"))
            submitted_charges = _safe_float(row.get("PSPS_SUBMITTED_CHARGE_AMT"))
            allowed_charges = _safe_float(row.get("PSPS_ALLOWED_CHARGE_AMT"))
            payment = _safe_float(row.get("PSPS_NCH_PAYMENT_AMT"))

            if hcpcs not in agg:
                agg[hcpcs] = {
                    "total_services": 0.0,
                    "total_submitted_charges": 0.0,
                    "total_allowed_charges": 0.0,
                    "total_payment": 0.0,
                    "total_line_items": 0,
                }

            entry = agg[hcpcs]
            entry["total_services"] += services
            entry["total_submitted_charges"] += submitted_charges
            entry["total_allowed_charges"] += allowed_charges
            entry["total_payment"] += payment
            entry["total_line_items"] += 1

    _hcpcs_national = agg
    logger.info(
        "Aggregated %d rows into %d unique HCPCS codes",
        row_count, len(agg),
    )
    return _hcpcs_national


def get_hcpcs_national_stats(hcpcs: str) -> dict:
    """
    For a given HCPCS code, return: total services nationally, total payments,
    avg payment per service, total providers (line items). Powers the provider
    anomaly module with real national benchmarks.
    """
    if not hcpcs:
        return {"error": "hcpcs parameter is required"}

    index = _ensure_hcpcs_national()
    hcpcs_upper = hcpcs.upper().strip()
    entry = index.get(hcpcs_upper)

    if not entry:
        return {
            "hcpcs_code": hcpcs_upper,
            "found": False,
            "message": f"No data found for HCPCS code {hcpcs_upper}",
        }

    total_services = entry["total_services"]
    total_payment = entry["total_payment"]
    avg_payment = round(total_payment / total_services, 2) if total_services > 0 else 0

    return {
        "hcpcs_code": hcpcs_upper,
        "found": True,
        "total_services": round(total_services, 2),
        "total_submitted_charges": round(entry["total_submitted_charges"], 2),
        "total_allowed_charges": round(entry["total_allowed_charges"], 2),
        "total_payment": round(total_payment, 2),
        "avg_payment_per_service": avg_payment,
        "avg_submitted_charge_per_service": (
            round(entry["total_submitted_charges"] / total_services, 2)
            if total_services > 0 else 0
        ),
        "total_line_items": entry["total_line_items"],
        "data_source": "CMS Physician/Supplier Procedure Summary (national)",
    }


# ---------------------------------------------------------------------------
# 7. Opioid Patterns (Medicare + Medicaid)
# ---------------------------------------------------------------------------

def _ensure_opioid_data() -> Dict[str, dict]:
    """
    Aggregate both opioid CSVs by state on load to minimize memory.
    """
    global _opioid_by_state
    if _opioid_by_state is not None:
        return _opioid_by_state

    _opioid_by_state = {}

    # Medicare opioid (Part D)
    fname_medicare = "partd_opioid_geo.csv"
    if _file_exists(fname_medicare):
        logger.info("Loading partd_opioid_geo.csv (aggregating by state) ...")
        with open(_csv_path(fname_medicare), "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                geo_lvl = (row.get("Prscrbr_Geo_Lvl") or "").strip()
                if geo_lvl.lower() != "state":
                    continue
                state_desc = (row.get("Prscrbr_Geo_Desc") or "").strip()
                state_cd = (row.get("Prscrbr_Geo_Cd") or "").strip().upper()
                year = _safe_int(row.get("Year"))

                key = state_cd if state_cd else state_desc.upper()
                if key not in _opioid_by_state:
                    _opioid_by_state[key] = {
                        "state": state_desc,
                        "state_code": state_cd,
                        "medicare": {},
                        "medicaid": {},
                    }

                _opioid_by_state[key]["medicare"][year] = {
                    "total_prescribers": _safe_int(row.get("Tot_Prscrbrs")),
                    "total_opioid_prescribers": _safe_int(row.get("Tot_Opioid_Prscrbrs")),
                    "total_opioid_claims": _safe_int(row.get("Tot_Opioid_Clms")),
                    "total_claims": _safe_int(row.get("Tot_Clms")),
                    "opioid_prescribing_rate": _safe_float(row.get("Opioid_Prscrbng_Rate")),
                    "opioid_rate_5y_change": _safe_float(row.get("Opioid_Prscrbng_Rate_5Y_Chg")),
                    "opioid_rate_1y_change": _safe_float(row.get("Opioid_Prscrbng_Rate_1Y_Chg")),
                    "la_opioid_claims": _safe_int(row.get("LA_Tot_Opioid_Clms")),
                    "la_opioid_prescribing_rate": _safe_float(row.get("LA_Opioid_Prscrbng_Rate")),
                }
    else:
        logger.warning("Medicare opioid file not found: %s", fname_medicare)

    # Medicaid opioid
    fname_medicaid = "medicaid_opioid_geo.csv"
    if _file_exists(fname_medicaid):
        logger.info("Loading medicaid_opioid_geo.csv (aggregating by state) ...")
        with open(_csv_path(fname_medicaid), "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                geo_lvl = (row.get("Geo_Lvl") or "").strip()
                if geo_lvl.lower() != "state":
                    continue
                state_desc = (row.get("Geo_Desc") or "").strip()
                state_cd = (row.get("Geo_Cd") or "").strip().upper()
                year = _safe_int(row.get("Year"))
                plan_type = (row.get("Plan_Type") or "Overall").strip()

                key = state_cd if state_cd else state_desc.upper()
                if key not in _opioid_by_state:
                    _opioid_by_state[key] = {
                        "state": state_desc,
                        "state_code": state_cd,
                        "medicare": {},
                        "medicaid": {},
                    }

                # Use plan_type as sub-key if not "Overall"
                year_key = year if plan_type.lower() == "overall" else f"{year}_{plan_type}"
                _opioid_by_state[key]["medicaid"][year_key] = {
                    "plan_type": plan_type,
                    "total_opioid_claims": _safe_int(row.get("Tot_Opioid_Clms")),
                    "total_claims": _safe_int(row.get("Tot_Clms")),
                    "opioid_prescribing_rate": _safe_float(row.get("Opioid_Prscrbng_Rate")),
                    "opioid_rate_5y_change": _safe_float(row.get("Opioid_Prscrbng_Rate_5Y_Chg")),
                    "opioid_rate_1y_change": _safe_float(row.get("Opioid_Prscrbng_Rate_1Y_Chg")),
                    "la_opioid_claims": _safe_int(row.get("LA_Tot_Opioid_Clms")),
                    "la_opioid_prescribing_rate": _safe_float(row.get("LA_Opioid_Prscrbng_Rate")),
                }
    else:
        logger.warning("Medicaid opioid file not found: %s", fname_medicaid)

    logger.info("Aggregated opioid data for %d states", len(_opioid_by_state))
    return _opioid_by_state


def get_opioid_patterns(state: str = None) -> dict:
    """
    Return Medicare and Medicaid opioid prescribing rates by state,
    with national averages for comparison.
    """
    data = _ensure_opioid_data()

    # Compute national averages from all states
    all_medicare_rates = []
    all_medicaid_rates = []
    for entry in data.values():
        for yr_data in entry["medicare"].values():
            rate = yr_data.get("opioid_prescribing_rate", 0)
            if rate > 0:
                all_medicare_rates.append(rate)
        for yr_data in entry["medicaid"].values():
            rate = yr_data.get("opioid_prescribing_rate", 0)
            if rate > 0:
                all_medicaid_rates.append(rate)

    national_avg_medicare = (
        round(sum(all_medicare_rates) / len(all_medicare_rates), 4)
        if all_medicare_rates else 0
    )
    national_avg_medicaid = (
        round(sum(all_medicaid_rates) / len(all_medicaid_rates), 4)
        if all_medicaid_rates else 0
    )

    if state:
        state_upper = state.upper()
        entry = data.get(state_upper)
        if not entry:
            # Try matching by description
            for k, v in data.items():
                if v["state"].upper() == state_upper:
                    entry = v
                    break

        if not entry:
            return {
                "state": state_upper,
                "found": False,
                "national_avg_medicare_opioid_rate": national_avg_medicare,
                "national_avg_medicaid_opioid_rate": national_avg_medicaid,
            }

        return {
            "state": entry["state"],
            "state_code": entry["state_code"],
            "found": True,
            "medicare_opioid_data": entry["medicare"],
            "medicaid_opioid_data": entry["medicaid"],
            "national_avg_medicare_opioid_rate": national_avg_medicare,
            "national_avg_medicaid_opioid_rate": national_avg_medicaid,
            "data_source": "CMS Part D Opioid Prescribing + Medicaid Opioid Geographic",
        }

    # Return summary for all states
    state_summaries = []
    for key, entry in sorted(data.items()):
        # Get latest year of Medicare data
        latest_medicare = {}
        if entry["medicare"]:
            max_yr = max(entry["medicare"].keys())
            latest_medicare = entry["medicare"][max_yr]

        latest_medicaid = {}
        # Get latest "Overall" medicaid data (integer year keys)
        medicaid_int_years = [k for k in entry["medicaid"].keys() if isinstance(k, int)]
        if medicaid_int_years:
            max_yr = max(medicaid_int_years)
            latest_medicaid = entry["medicaid"][max_yr]

        state_summaries.append({
            "state": entry["state"],
            "state_code": entry["state_code"],
            "medicare_opioid_rate": latest_medicare.get("opioid_prescribing_rate", 0),
            "medicaid_opioid_rate": latest_medicaid.get("opioid_prescribing_rate", 0),
            "medicare_opioid_claims": latest_medicare.get("total_opioid_claims", 0),
            "medicaid_opioid_claims": latest_medicaid.get("total_opioid_claims", 0),
        })

    state_summaries.sort(key=lambda x: x["medicare_opioid_rate"], reverse=True)

    return {
        "total_states": len(state_summaries),
        "national_avg_medicare_opioid_rate": national_avg_medicare,
        "national_avg_medicaid_opioid_rate": national_avg_medicaid,
        "states": state_summaries,
        "data_source": "CMS Part D Opioid Prescribing + Medicaid Opioid Geographic",
    }


# ---------------------------------------------------------------------------
# 8. Dataset Inventory
# ---------------------------------------------------------------------------

_DATASETS = [
    ("state_drug_utilization_2023.csv", "State Drug Utilization 2023", "Medicaid drug utilization by state, NDC, quarter"),
    ("state_drug_utilization_2024.csv", "State Drug Utilization 2024", "Medicaid drug utilization by state, NDC, quarter"),
    ("state_drug_utilization_2025.csv", "State Drug Utilization 2025", "Medicaid drug utilization by state, NDC, quarter"),
    ("medicaid_spending_by_drug.csv", "Medicaid Spending by Drug", "Brand/generic spending trends 2019-2023"),
    ("partb_discarded_units.csv", "Part B Discarded Drug Units", "HCPCS drug waste/discarded unit analysis"),
    ("partd_prescribers_geo_drug.csv", "Part D Prescribers by Geo+Drug", "Prescribing patterns by region and drug"),
    ("partd_prescribers_by_provider.csv", "Part D Prescribers by Provider", "Per-NPI prescribing summary"),
    ("partd_opioid_geo.csv", "Part D Opioid Geographic", "Medicare opioid prescribing by geography"),
    ("medicaid_opioid_geo.csv", "Medicaid Opioid Geographic", "Medicaid opioid prescribing patterns"),
    ("physician_by_provider.csv", "Physician by Provider", "Per-NPI physician utilization summary"),
    ("physician_geo_service.csv", "Physician Geo Service", "HCPCS utilization by geography"),
    ("physician_supplier_procedure_summary.csv", "Physician/Supplier Procedure Summary", "National HCPCS procedure-level stats"),
    ("nadac_current.csv", "NADAC Current", "National Average Drug Acquisition Cost"),
    ("partb_drug_spending.csv", "Part B Drug Spending", "Medicare Part B drug spending"),
    ("partb_quarterly_spending.csv", "Part B Quarterly Spending", "Medicare Part B quarterly drug spending"),
    ("partd_drug_spending.csv", "Part D Drug Spending", "Medicare Part D drug spending"),
    ("partd_quarterly_spending.csv", "Part D Quarterly Spending", "Medicare Part D quarterly drug spending"),
]


def get_inventory() -> list:
    """List all available CMS datasets with row counts and file sizes."""
    global _inventory_cache
    if _inventory_cache is not None:
        return _inventory_cache

    results = []
    for fname, display_name, description in _DATASETS:
        path = _csv_path(fname)
        exists = os.path.exists(path)
        size_bytes = os.path.getsize(path) if exists else 0
        size_mb = round(size_bytes / (1024 * 1024), 1)

        row_count = 0
        if exists:
            # Quick count without loading into memory
            with open(path, "r", encoding="utf-8") as fh:
                next(fh, None)  # skip header
                for _ in fh:
                    row_count += 1

        results.append({
            "filename": fname,
            "name": display_name,
            "description": description,
            "available": exists,
            "size_mb": size_mb,
            "row_count": row_count,
        })

    _inventory_cache = results
    return _inventory_cache

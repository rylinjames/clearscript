"""
CMS Part D Data Service.

Provides pre-computed benchmark statistics derived from CMS Medicare Part D
Public Use Files (PUFs) and the IRA Medicare Drug Price Negotiation program.
Benchmarks a parsed employer formulary against Part D plan averages.
"""

import logging
from typing import List, Dict, Any

from services import cms_spending_service

logger = logging.getLogger("clearscript.cms_partd_service")

# ---------------------------------------------------------------------------
# IRA Selected Drugs — Medicare Price Negotiation (announced Aug 2024,
# negotiated Maximum Fair Prices effective Jan 2026)
# ---------------------------------------------------------------------------

IRA_SELECTED_DRUGS: List[Dict[str, Any]] = [
    {
        "drug_name": "Eliquis",
        "generic_name": "apixaban",
        "manufacturer": "Bristol-Myers Squibb / Pfizer",
        "condition": "Blood clots / stroke prevention",
        "ndc_prefix": "00003-0893",
        "current_list_price_30day": 521.00,
        "negotiated_max_fair_price_30day": 231.00,
        "savings_pct": 0.556,
        "part_d_enrollees_using": 3_700_000,
    },
    {
        "drug_name": "Jardiance",
        "generic_name": "empagliflozin",
        "manufacturer": "Boehringer Ingelheim / Eli Lilly",
        "condition": "Diabetes / heart failure",
        "ndc_prefix": "00597-0142",
        "current_list_price_30day": 573.00,
        "negotiated_max_fair_price_30day": 197.00,
        "savings_pct": 0.656,
        "part_d_enrollees_using": 1_573_000,
    },
    {
        "drug_name": "Xarelto",
        "generic_name": "rivaroxaban",
        "manufacturer": "Janssen (Johnson & Johnson)",
        "condition": "Blood clots / stroke prevention",
        "ndc_prefix": "50458-0580",
        "current_list_price_30day": 517.00,
        "negotiated_max_fair_price_30day": 197.00,
        "savings_pct": 0.619,
        "part_d_enrollees_using": 1_337_000,
    },
    {
        "drug_name": "Januvia",
        "generic_name": "sitagliptin",
        "manufacturer": "Merck",
        "condition": "Type 2 diabetes",
        "ndc_prefix": "00006-0277",
        "current_list_price_30day": 527.00,
        "negotiated_max_fair_price_30day": 113.00,
        "savings_pct": 0.786,
        "part_d_enrollees_using": 869_000,
    },
    {
        "drug_name": "Farxiga",
        "generic_name": "dapagliflozin",
        "manufacturer": "AstraZeneca",
        "condition": "Diabetes / heart failure / chronic kidney disease",
        "ndc_prefix": "00310-6205",
        "current_list_price_30day": 556.00,
        "negotiated_max_fair_price_30day": 178.50,
        "savings_pct": 0.679,
        "part_d_enrollees_using": 799_000,
    },
    {
        "drug_name": "Entresto",
        "generic_name": "sacubitril/valsartan",
        "manufacturer": "Novartis",
        "condition": "Heart failure",
        "ndc_prefix": "00078-0620",
        "current_list_price_30day": 628.00,
        "negotiated_max_fair_price_30day": 295.00,
        "savings_pct": 0.530,
        "part_d_enrollees_using": 688_000,
    },
    {
        "drug_name": "Enbrel",
        "generic_name": "etanercept",
        "manufacturer": "Amgen",
        "condition": "Rheumatoid arthritis / psoriasis",
        "ndc_prefix": "58406-0425",
        "current_list_price_30day": 7_106.00,
        "negotiated_max_fair_price_30day": 2_355.00,
        "savings_pct": 0.668,
        "part_d_enrollees_using": 48_000,
    },
    {
        "drug_name": "Imbruvica",
        "generic_name": "ibrutinib",
        "manufacturer": "Pharmacyclics (AbbVie) / Janssen",
        "condition": "Blood cancers",
        "ndc_prefix": "57962-0140",
        "current_list_price_30day": 14_934.00,
        "negotiated_max_fair_price_30day": 9_319.00,
        "savings_pct": 0.376,
        "part_d_enrollees_using": 20_000,
    },
    {
        "drug_name": "Stelara",
        "generic_name": "ustekinumab",
        "manufacturer": "Janssen (Johnson & Johnson)",
        "condition": "Psoriasis / Crohn's disease / ulcerative colitis",
        "ndc_prefix": "57894-0030",
        "current_list_price_30day": 13_836.00,
        "negotiated_max_fair_price_30day": 4_695.00,
        "savings_pct": 0.661,
        "part_d_enrollees_using": 22_000,
    },
    {
        "drug_name": "Fiasp/NovoLog",
        "generic_name": "insulin aspart",
        "manufacturer": "Novo Nordisk",
        "condition": "Diabetes (insulin)",
        "ndc_prefix": "00169-4164",
        "current_list_price_30day": 495.00,
        "negotiated_max_fair_price_30day": 119.00,
        "savings_pct": 0.760,
        "part_d_enrollees_using": 777_000,
    },
]

# ---------------------------------------------------------------------------
# Part D benchmark constants (derived from CMS PUF methodology)
# ---------------------------------------------------------------------------

PARTD_PLAN_COUNT = 4_217

PARTD_TIER_DISTRIBUTION = {
    "tier_1_preferred_generic_pct": 28.4,
    "tier_2_generic_pct": 22.1,
    "tier_3_preferred_brand_pct": 18.7,
    "tier_4_nonpreferred_pct": 15.3,
    "tier_5_specialty_pct": 12.8,
    "tier_6_select_care_pct": 2.7,
}

PARTD_UM_RATES = {
    "prior_authorization": {"mean_pct": 24.8, "p10_pct": 14.2, "p90_pct": 38.5},
    "quantity_limit": {"mean_pct": 18.3, "p10_pct": 9.1, "p90_pct": 30.6},
    "step_therapy": {"mean_pct": 8.9, "p10_pct": 3.2, "p90_pct": 17.4},
}

PARTD_AVG_FORMULARY_SIZE = 3_812
PARTD_AVG_EXCLUDED_DRUGS = 142

INSULIN_COST_SHARING_CAP = 35.00  # IRA provision effective Jan 2025


# ---------------------------------------------------------------------------
# Highly-covered drugs — drugs covered by > 90% of Part D plans
# Used to flag employer exclusions that are unusual
# ---------------------------------------------------------------------------

_HIGHLY_COVERED_DRUGS = {
    "ATORVASTATIN", "LISINOPRIL", "METFORMIN", "AMLODIPINE", "OMEPRAZOLE",
    "SERTRALINE", "LEVOTHYROXINE", "ALBUTEROL", "GABAPENTIN", "LOSARTAN",
    "METOPROLOL", "PANTOPRAZOLE", "MONTELUKAST", "ESCITALOPRAM",
    "ROSUVASTATIN", "HYDROCHLOROTHIAZIDE", "AMOXICILLIN", "AZITHROMYCIN",
    "PREDNISONE", "MELOXICAM", "CLOPIDOGREL", "BUPROPION", "TRAZODONE",
    "DULOXETINE", "CARVEDILOL", "SPIRONOLACTONE", "TAMSULOSIN",
    "FLUTICASONE", "PREGABALIN", "CYCLOBENZAPRINE", "VALACYCLOVIR",
    "ELIQUIS", "JARDIANCE", "XARELTO", "ENTRESTO", "INSULIN GLARGINE",
    "INSULIN ASPART", "LANTUS", "HUMALOG",
}

# Median Part D tier assignment for common drugs
_PARTD_MEDIAN_TIERS: Dict[str, int] = {
    "ATORVASTATIN": 1, "LISINOPRIL": 1, "METFORMIN": 1, "AMLODIPINE": 1,
    "OMEPRAZOLE": 1, "SERTRALINE": 1, "LEVOTHYROXINE": 1, "ALBUTEROL": 1,
    "GABAPENTIN": 1, "LOSARTAN": 1, "METOPROLOL": 1, "ROSUVASTATIN": 1,
    "HYDROCHLOROTHIAZIDE": 1, "MONTELUKAST": 1, "ESCITALOPRAM": 1,
    "PANTOPRAZOLE": 1, "DULOXETINE": 1, "PREGABALIN": 2,
    "TRAZODONE": 1, "MELOXICAM": 1, "CLOPIDOGREL": 1,
    "BUPROPION": 1, "AMOXICILLIN": 1, "AZITHROMYCIN": 1,
    "PREDNISONE": 1, "ELIQUIS": 3, "JARDIANCE": 3, "XARELTO": 3,
    "ENTRESTO": 3, "OZEMPIC": 3, "HUMIRA": 5, "STELARA": 5,
    "KEYTRUDA": 5, "DUPIXENT": 5, "INSULIN GLARGINE": 2,
    "LIPITOR": 4, "CRESTOR": 4, "NEXIUM": 4,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_partd_benchmarks() -> dict:
    """
    Return CMS Part D benchmark statistics, enriched with real spending
    data from the CMS Part D Drug Spending Dashboard where available.

    Combines pre-computed structural benchmarks (tier distribution, UM rates)
    with actual aggregate spending figures from the downloaded dataset.
    """
    # Pull real aggregate stats from the Part D spending CSV
    try:
        real_stats = cms_spending_service.get_partd_aggregate_stats()
        has_real_data = real_stats.get("total_drugs_tracked", 0) > 0
    except Exception as e:
        logger.warning("Could not load real Part D spending data: %s", e)
        real_stats = {}
        has_real_data = False

    benchmarks = {
        "source": "CMS Medicare Part D Public Use Files (PUF) + Part D Drug Spending Dashboard",
        "data_period": "2023 (spending data), Q4 2025 (formulary structure)",
        "total_plans": PARTD_PLAN_COUNT,
        "average_formulary_size_ndcs": PARTD_AVG_FORMULARY_SIZE,
        "tier_distribution_pct": PARTD_TIER_DISTRIBUTION,
        "utilization_management_rates": PARTD_UM_RATES,
        "average_excluded_drugs_per_plan": PARTD_AVG_EXCLUDED_DRUGS,
        "insulin_cost_sharing_cap_monthly": INSULIN_COST_SHARING_CAP,
        "ira_selected_drugs_count": len(IRA_SELECTED_DRUGS),
        "ira_total_enrollees_affected": sum(
            d["part_d_enrollees_using"] for d in IRA_SELECTED_DRUGS
        ),
        "methodology_notes": [
            "Tier distribution computed across all non-LIS Part D plans in the Basic Drugs Formulary File",
            "UM rates (PA/QL/ST) computed as the share of formulary NDCs with each flag set to Y",
            "Excluded drugs estimated from NDCs present in < 5% of plan formularies vs FDA-approved list",
            "IRA Maximum Fair Prices are published by CMS and effective January 2026",
            "Insulin $35/month cost-sharing cap applies to all Part D plans under IRA Section 11407",
            "Spending figures sourced from CMS Medicare Part D Drug Spending Dashboard (2023 data year)",
        ],
    }

    # Enrich with real spending data when available
    if has_real_data:
        benchmarks["spending_data"] = {
            "total_drugs_tracked": real_stats.get("total_drugs_tracked"),
            "total_medicare_partd_spending_2023": real_stats.get("total_spending_2023"),
            "total_claims_2023": real_stats.get("total_claims_2023"),
            "total_beneficiaries_2023": real_stats.get("total_beneficiaries_2023"),
            "avg_cost_per_claim": real_stats.get("avg_cost_per_claim"),
            "top_10_spending_concentration_pct": real_stats.get("top_10_spending_concentration_pct"),
            "avg_yoy_cost_change_per_unit": real_stats.get("avg_yoy_cost_change_per_unit"),
            "data_source": real_stats.get("data_source"),
        }
        benchmarks["top_drugs_by_spending"] = real_stats.get("top_10_drugs_by_spending", [])
    else:
        benchmarks["spending_data"] = None
        benchmarks["top_drugs_by_spending"] = []

    return benchmarks


def benchmark_formulary_against_partd(formulary_rows: List[Dict[str, Any]]) -> dict:
    """
    Benchmark a parsed formulary (from formulary_service.parse_formulary_pdf)
    against CMS Part D plan averages.

    Returns tier distribution comparison, UM rate comparison, coverage gap
    flags, tier mismatch flags, and an overall competitiveness score (0-100).
    """
    if not formulary_rows:
        return {"error": "No formulary rows provided", "competitiveness_score": 0}

    total = len(formulary_rows)

    # --- Tier distribution ---
    tier_counts: Dict[int, int] = {}
    for row in formulary_rows:
        t = row.get("tier", 0)
        tier_counts[t] = tier_counts.get(t, 0) + 1

    employer_tier_dist = {}
    for t in range(1, 7):
        employer_tier_dist[f"tier_{t}_pct"] = round(
            tier_counts.get(t, 0) / total * 100, 1
        )

    # --- UM rates ---
    pa_count = sum(1 for r in formulary_rows if r.get("pa"))
    ql_count = sum(1 for r in formulary_rows if r.get("ql"))
    st_count = sum(1 for r in formulary_rows if r.get("st"))

    employer_pa_pct = round(pa_count / total * 100, 1)
    employer_ql_pct = round(ql_count / total * 100, 1)
    employer_st_pct = round(st_count / total * 100, 1)

    # --- Coverage gap flags ---
    # Extract drug names from the formulary
    formulary_names = set()
    for row in formulary_rows:
        name = row.get("drug_name", "").upper().strip()
        # Take the first word as the base name for matching
        base = name.split()[0] if name else ""
        formulary_names.add(name)
        formulary_names.add(base)

    excluded_but_covered = []
    for drug in _HIGHLY_COVERED_DRUGS:
        # Check if any formulary entry matches
        found = any(
            drug in fn or fn.startswith(drug.split()[0])
            for fn in formulary_names
        )
        if not found:
            excluded_but_covered.append({
                "drug_name": drug,
                "partd_coverage_pct": ">90%",
                "flag": "Excluded from employer formulary but covered by >90% of Part D plans",
            })

    # --- Tier mismatch flags ---
    tier_mismatches = []
    for row in formulary_rows:
        name_upper = row.get("drug_name", "").upper().strip()
        base_name = name_upper.split()[0]
        partd_tier = _PARTD_MEDIAN_TIERS.get(name_upper) or _PARTD_MEDIAN_TIERS.get(base_name)
        if partd_tier is not None:
            employer_tier = row.get("tier", 0)
            if employer_tier >= partd_tier + 2:
                tier_mismatches.append({
                    "drug_name": row.get("drug_name", name_upper),
                    "employer_tier": employer_tier,
                    "partd_median_tier": partd_tier,
                    "tier_gap": employer_tier - partd_tier,
                    "flag": "Employer tier significantly higher than Part D median",
                })

    # --- Competitiveness score (0-100) ---
    # Higher = more competitive (closer to Part D averages or better)
    score = 100.0

    # Penalize for high PA rate vs Part D
    pa_diff = employer_pa_pct - PARTD_UM_RATES["prior_authorization"]["mean_pct"]
    if pa_diff > 0:
        score -= min(pa_diff * 0.8, 20)

    # Penalize for high QL rate vs Part D
    ql_diff = employer_ql_pct - PARTD_UM_RATES["quantity_limit"]["mean_pct"]
    if ql_diff > 0:
        score -= min(ql_diff * 0.6, 15)

    # Penalize for high ST rate vs Part D
    st_diff = employer_st_pct - PARTD_UM_RATES["step_therapy"]["mean_pct"]
    if st_diff > 0:
        score -= min(st_diff * 0.7, 10)

    # Penalize for excluding commonly-covered drugs
    score -= min(len(excluded_but_covered) * 1.5, 25)

    # Penalize for tier mismatches
    score -= min(len(tier_mismatches) * 2.0, 15)

    # Reward for having a large formulary relative to Part D average
    size_ratio = total / PARTD_AVG_FORMULARY_SIZE
    if size_ratio >= 0.8:
        score += min((size_ratio - 0.8) * 20, 10)
    else:
        score -= min((0.8 - size_ratio) * 30, 15)

    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "formulary_size": total,
        "partd_avg_formulary_size": PARTD_AVG_FORMULARY_SIZE,
        "tier_distribution": {
            "employer": employer_tier_dist,
            "partd_average": PARTD_TIER_DISTRIBUTION,
        },
        "utilization_management": {
            "employer": {
                "pa_pct": employer_pa_pct,
                "ql_pct": employer_ql_pct,
                "st_pct": employer_st_pct,
            },
            "partd_average": PARTD_UM_RATES,
        },
        "coverage_gaps": excluded_but_covered,
        "coverage_gaps_count": len(excluded_but_covered),
        "tier_mismatches": tier_mismatches,
        "tier_mismatches_count": len(tier_mismatches),
        "competitiveness_score": score,
        "score_interpretation": _interpret_score(score),
        "insulin_cost_sharing_cap": INSULIN_COST_SHARING_CAP,
    }


def get_ira_selected_drugs() -> List[Dict[str, Any]]:
    """
    Return the 10 drugs selected for Medicare Price Negotiation under the
    Inflation Reduction Act, with their negotiated Maximum Fair Prices.
    """
    return IRA_SELECTED_DRUGS


def _interpret_score(score: float) -> str:
    """Return a human-readable interpretation of the competitiveness score."""
    if score >= 85:
        return (
            "Excellent. The employer formulary is highly competitive with "
            "Medicare Part D plans in terms of coverage breadth, tier placement, "
            "and utilization management burden."
        )
    elif score >= 70:
        return (
            "Good. The employer formulary is broadly comparable to Part D "
            "standards, with some areas where coverage or tier assignments "
            "could be improved."
        )
    elif score >= 50:
        return (
            "Fair. The employer formulary shows notable gaps compared to "
            "Part D benchmarks. Members may face higher cost-sharing or "
            "restricted access to commonly-covered drugs."
        )
    else:
        return (
            "Below average. The employer formulary is significantly less "
            "competitive than typical Part D plans. Review excluded drugs "
            "and elevated tier assignments for potential plan improvements."
        )

"""
Copay Accumulator Impact Estimator — model the financial impact of PBM copay
accumulator adjustment programs on plan members.

PBMs use accumulator programs to prevent manufacturer copay assistance from
counting toward a patient's deductible or out-of-pocket maximum.  This means
patients using copay cards may exhaust the manufacturer subsidy AND still owe
their full deductible — effectively paying twice.

This service estimates the per-member and aggregate financial impact.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("clearscript.copay_accumulator_service")

# ---------------------------------------------------------------------------
# Reference list: drugs with known manufacturer copay assistance programs
# ---------------------------------------------------------------------------

COPAY_ASSISTANCE_DRUGS: list[dict] = [
    # Autoimmune / Immunology
    {"drug_name": "HUMIRA", "generic": "adalimumab", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 14_400, "annual_drug_cost": 84_000},
    {"drug_name": "STELARA", "generic": "ustekinumab", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 13_200, "annual_drug_cost": 78_000},
    {"drug_name": "DUPIXENT", "generic": "dupilumab", "therapeutic_class": "Autoimmune/Dermatology", "annual_copay_card_value": 13_000, "annual_drug_cost": 52_000},
    {"drug_name": "SKYRIZI", "generic": "risankizumab", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 12_000, "annual_drug_cost": 66_000},
    {"drug_name": "RINVOQ", "generic": "upadacitinib", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 12_000, "annual_drug_cost": 72_000},
    {"drug_name": "TREMFYA", "generic": "guselkumab", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 11_000, "annual_drug_cost": 58_000},
    {"drug_name": "COSENTYX", "generic": "secukinumab", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 12_000, "annual_drug_cost": 72_000},
    {"drug_name": "OTEZLA", "generic": "apremilast", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 9_000, "annual_drug_cost": 44_000},
    {"drug_name": "ENBREL", "generic": "etanercept", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 12_000, "annual_drug_cost": 72_000},
    {"drug_name": "XELJANZ", "generic": "tofacitinib", "therapeutic_class": "Autoimmune", "annual_copay_card_value": 10_000, "annual_drug_cost": 62_000},
    # Oncology
    {"drug_name": "KEYTRUDA", "generic": "pembrolizumab", "therapeutic_class": "Oncology", "annual_copay_card_value": 15_000, "annual_drug_cost": 175_000},
    {"drug_name": "REVLIMID", "generic": "lenalidomide", "therapeutic_class": "Oncology", "annual_copay_card_value": 14_000, "annual_drug_cost": 180_000},
    {"drug_name": "IMBRUVICA", "generic": "ibrutinib", "therapeutic_class": "Oncology", "annual_copay_card_value": 14_000, "annual_drug_cost": 170_000},
    {"drug_name": "IBRANCE", "generic": "palbociclib", "therapeutic_class": "Oncology", "annual_copay_card_value": 13_000, "annual_drug_cost": 160_000},
    {"drug_name": "TAGRISSO", "generic": "osimertinib", "therapeutic_class": "Oncology", "annual_copay_card_value": 13_000, "annual_drug_cost": 165_000},
    {"drug_name": "XTANDI", "generic": "enzalutamide", "therapeutic_class": "Oncology", "annual_copay_card_value": 13_000, "annual_drug_cost": 155_000},
    {"drug_name": "POMALYST", "generic": "pomalidomide", "therapeutic_class": "Oncology", "annual_copay_card_value": 14_000, "annual_drug_cost": 185_000},
    {"drug_name": "CALQUENCE", "generic": "acalabrutinib", "therapeutic_class": "Oncology", "annual_copay_card_value": 12_000, "annual_drug_cost": 155_000},
    # Diabetes / Metabolic
    {"drug_name": "OZEMPIC", "generic": "semaglutide", "therapeutic_class": "Diabetes", "annual_copay_card_value": 9_000, "annual_drug_cost": 12_000},
    {"drug_name": "JARDIANCE", "generic": "empagliflozin", "therapeutic_class": "Diabetes", "annual_copay_card_value": 6_000, "annual_drug_cost": 7_200},
    {"drug_name": "TRULICITY", "generic": "dulaglutide", "therapeutic_class": "Diabetes", "annual_copay_card_value": 8_000, "annual_drug_cost": 10_800},
    {"drug_name": "MOUNJARO", "generic": "tirzepatide", "therapeutic_class": "Diabetes", "annual_copay_card_value": 9_000, "annual_drug_cost": 13_200},
    {"drug_name": "FARXIGA", "generic": "dapagliflozin", "therapeutic_class": "Diabetes", "annual_copay_card_value": 5_500, "annual_drug_cost": 6_600},
    # Cardiovascular
    {"drug_name": "ELIQUIS", "generic": "apixaban", "therapeutic_class": "Cardiovascular", "annual_copay_card_value": 6_600, "annual_drug_cost": 7_200},
    {"drug_name": "XARELTO", "generic": "rivaroxaban", "therapeutic_class": "Cardiovascular", "annual_copay_card_value": 6_000, "annual_drug_cost": 6_600},
    {"drug_name": "ENTRESTO", "generic": "sacubitril/valsartan", "therapeutic_class": "Cardiovascular", "annual_copay_card_value": 7_200, "annual_drug_cost": 7_800},
    {"drug_name": "REPATHA", "generic": "evolocumab", "therapeutic_class": "Cardiovascular", "annual_copay_card_value": 8_000, "annual_drug_cost": 14_400},
    # Multiple Sclerosis
    {"drug_name": "OCREVUS", "generic": "ocrelizumab", "therapeutic_class": "Multiple Sclerosis", "annual_copay_card_value": 15_000, "annual_drug_cost": 70_000},
    {"drug_name": "KESIMPTA", "generic": "ofatumumab", "therapeutic_class": "Multiple Sclerosis", "annual_copay_card_value": 12_000, "annual_drug_cost": 85_000},
    {"drug_name": "AUBAGIO", "generic": "teriflunomide", "therapeutic_class": "Multiple Sclerosis", "annual_copay_card_value": 10_000, "annual_drug_cost": 52_000},
]

# Build a lookup by normalized name
_COPAY_DRUG_LOOKUP: dict[str, dict] = {
    d["drug_name"].upper(): d for d in COPAY_ASSISTANCE_DRUGS
}


# ---------------------------------------------------------------------------
# Core estimation
# ---------------------------------------------------------------------------

def estimate_accumulator_impact(
    claims: list[dict],
    deductible: float = 3_000.0,
    oop_max: float = 8_700.0,
) -> dict:
    """
    Estimate the financial impact of a copay accumulator adjustment program
    on a set of claims.

    Parameters
    ----------
    claims : list[dict]
        Each claim should have at minimum: member_id, drug_name, paid_amount.
        Optional: quantity, days_supply.
    deductible : float
        Annual individual deductible (default $3,000).
    oop_max : float
        Annual individual out-of-pocket maximum (default $8,700 — ACA limit).

    Returns
    -------
    dict with estimated impact metrics.
    """
    if not claims:
        logger.info("No claims provided — returning demo impact estimate")
        return _demo_impact(deductible, oop_max)

    # Identify members on copay-assistance-eligible drugs
    member_drugs: dict[str, set[str]] = {}  # member_id -> {DRUG_NAME, ...}
    member_spend: dict[str, float] = {}  # member_id -> total paid

    for claim in claims:
        mid = str(claim.get("member_id", "unknown"))
        drug = str(claim.get("drug_name", "")).upper().strip()
        paid = float(claim.get("paid_amount", 0))

        member_spend[mid] = member_spend.get(mid, 0) + paid
        member_drugs.setdefault(mid, set()).add(drug)

    # Find affected members
    affected_members: dict[str, list[dict]] = {}
    for mid, drugs in member_drugs.items():
        matched = []
        for drug in drugs:
            ref = _COPAY_DRUG_LOOKUP.get(drug)
            if ref:
                matched.append(ref)
        if matched:
            affected_members[mid] = matched

    total_members = len(member_drugs)
    affected_count = len(affected_members)

    # Estimate captured copay assistance value
    total_captured_value = 0.0
    drug_impact: dict[str, dict] = {}

    for mid, matched_drugs in affected_members.items():
        for ref in matched_drugs:
            dname = ref["drug_name"]
            card_value = ref["annual_copay_card_value"]
            # Under accumulator: PBM captures the copay card value that would
            # have counted toward deductible. Effective capture = min of card
            # value and deductible, since that is the amount "not counted".
            captured = min(card_value, deductible)
            total_captured_value += captured

            if dname not in drug_impact:
                drug_impact[dname] = {
                    "drug_name": dname,
                    "generic": ref["generic"],
                    "therapeutic_class": ref["therapeutic_class"],
                    "annual_copay_card_value": card_value,
                    "members_affected": 0,
                    "total_captured": 0.0,
                }
            drug_impact[dname]["members_affected"] += 1
            drug_impact[dname]["total_captured"] += captured

    # Sort by total captured descending
    drug_impact_list = sorted(
        drug_impact.values(), key=lambda d: d["total_captured"], reverse=True
    )

    per_member_impact = round(total_captured_value / max(affected_count, 1), 2)

    # Recommendation logic
    if affected_count > total_members * 0.05:
        recommendation = (
            "Significant accumulator exposure detected. Negotiate a copay "
            "maximizer program instead — this allows copay card value to count "
            "toward deductible while the plan still benefits from manufacturer "
            "assistance. Estimated annual savings opportunity from switching: "
            f"${total_captured_value:,.0f}."
        )
        program_recommendation = "maximizer"
    elif affected_count > 0:
        recommendation = (
            "Moderate accumulator exposure. Consider negotiating accumulator "
            "program carve-outs for high-value specialty drugs where copay "
            "card values exceed $10,000/year."
        )
        program_recommendation = "hybrid"
    else:
        recommendation = (
            "Low accumulator exposure based on current claims. Standard "
            "accumulator program terms are acceptable."
        )
        program_recommendation = "accumulator"

    return {
        "total_members": total_members,
        "affected_members": affected_count,
        "affected_pct": round(affected_count / max(total_members, 1) * 100, 2),
        "total_captured_value": round(total_captured_value, 2),
        "per_affected_member_impact": per_member_impact,
        "deductible_assumed": deductible,
        "oop_max_assumed": oop_max,
        "drugs_with_impact": drug_impact_list,
        "top_5_drugs": drug_impact_list[:5],
        "recommendation": recommendation,
        "program_recommendation": program_recommendation,
    }


# ---------------------------------------------------------------------------
# Demo / mock data
# ---------------------------------------------------------------------------

def _demo_impact(deductible: float, oop_max: float) -> dict:
    """
    Return a realistic demo estimate based on a hypothetical 5,000-member
    employer plan.
    """
    total_members = 5_000
    # ~3% of members on specialty drugs with copay cards
    affected_count = 150

    # Estimate per-drug impact for demo
    demo_drugs = [
        {"drug_name": "HUMIRA", "generic": "adalimumab", "therapeutic_class": "Autoimmune",
         "annual_copay_card_value": 14_400, "members_affected": 35,
         "total_captured": 35 * min(14_400, deductible)},
        {"drug_name": "DUPIXENT", "generic": "dupilumab", "therapeutic_class": "Autoimmune/Dermatology",
         "annual_copay_card_value": 13_000, "members_affected": 22,
         "total_captured": 22 * min(13_000, deductible)},
        {"drug_name": "KEYTRUDA", "generic": "pembrolizumab", "therapeutic_class": "Oncology",
         "annual_copay_card_value": 15_000, "members_affected": 8,
         "total_captured": 8 * min(15_000, deductible)},
        {"drug_name": "OZEMPIC", "generic": "semaglutide", "therapeutic_class": "Diabetes",
         "annual_copay_card_value": 9_000, "members_affected": 40,
         "total_captured": 40 * min(9_000, deductible)},
        {"drug_name": "ELIQUIS", "generic": "apixaban", "therapeutic_class": "Cardiovascular",
         "annual_copay_card_value": 6_600, "members_affected": 28,
         "total_captured": 28 * min(6_600, deductible)},
        {"drug_name": "STELARA", "generic": "ustekinumab", "therapeutic_class": "Autoimmune",
         "annual_copay_card_value": 13_200, "members_affected": 12,
         "total_captured": 12 * min(13_200, deductible)},
        {"drug_name": "ENTRESTO", "generic": "sacubitril/valsartan", "therapeutic_class": "Cardiovascular",
         "annual_copay_card_value": 7_200, "members_affected": 5,
         "total_captured": 5 * min(7_200, deductible)},
    ]

    total_captured = sum(d["total_captured"] for d in demo_drugs)
    per_member = round(total_captured / affected_count, 2)

    return {
        "total_members": total_members,
        "affected_members": affected_count,
        "affected_pct": round(affected_count / total_members * 100, 2),
        "total_captured_value": round(total_captured, 2),
        "per_affected_member_impact": per_member,
        "deductible_assumed": deductible,
        "oop_max_assumed": oop_max,
        "drugs_with_impact": demo_drugs,
        "top_5_drugs": demo_drugs[:5],
        "recommendation": (
            "Significant accumulator exposure detected in demo data. For a "
            f"plan with {total_members:,} members, an estimated "
            f"${total_captured:,.0f}/year in manufacturer copay assistance is "
            "being captured by the PBM through accumulator programs. Negotiate "
            "a copay maximizer program to redirect this value toward member "
            "deductible satisfaction."
        ),
        "program_recommendation": "maximizer",
        "is_demo": True,
    }


def get_drug_list() -> list[dict]:
    """Return the reference list of drugs with known copay assistance programs."""
    return [
        {
            "drug_name": d["drug_name"],
            "generic": d["generic"],
            "therapeutic_class": d["therapeutic_class"],
            "annual_copay_card_value": d["annual_copay_card_value"],
            "annual_drug_cost": d["annual_drug_cost"],
            "copay_card_as_pct_of_cost": round(
                d["annual_copay_card_value"] / d["annual_drug_cost"] * 100, 1
            ),
        }
        for d in COPAY_ASSISTANCE_DRUGS
    ]

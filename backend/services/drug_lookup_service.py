"""
Drug Lookup Service.

Consolidated drug search across all ClearScript data sources: synthetic drug
master list, NADAC pricing, NDC/J-code crosswalks, and IRA selected drugs.
"""

import logging
import re
from typing import Dict, List, Any, Optional

from services.data_service import DRUGS
from services.ndc_service import JCODE_CROSSWALK
from services.cms_partd_service import IRA_SELECTED_DRUGS
from services import nadac_service
from services import cms_spending_service

logger = logging.getLogger("clearscript.drug_lookup_service")

# ---------------------------------------------------------------------------
# Internal indexes (built once on first access)
# ---------------------------------------------------------------------------

_drug_name_index: Optional[Dict[str, List[Dict]]] = None
_ndc_index: Optional[Dict[str, Dict]] = None
_jcode_ndc_index: Optional[Dict[str, Dict]] = None
_ira_name_index: Optional[Dict[str, Dict]] = None


def _ensure_indexes():
    """Build lookup indexes from the various data sources."""
    global _drug_name_index, _ndc_index, _jcode_ndc_index, _ira_name_index

    if _drug_name_index is not None:
        return

    # Drug name -> list of drug dicts (multiple NDCs may share a name token)
    _drug_name_index = {}
    for drug in DRUGS:
        tokens = _tokenize(drug["name"])
        for token in tokens:
            _drug_name_index.setdefault(token, []).append(drug)

    # NDC -> drug dict
    _ndc_index = {}
    for drug in DRUGS:
        _ndc_index[drug["ndc"]] = drug

    # NDC -> J-code crosswalk entry
    _jcode_ndc_index = {}
    for entry in JCODE_CROSSWALK:
        for ndc_rec in entry["ndcs"]:
            _jcode_ndc_index[ndc_rec["ndc"]] = {
                "jcode": entry["jcode"],
                "jcode_desc": entry["jcode_desc"],
                "therapy_class": entry["therapy_class"],
                "avg_cost_per_admin": entry["avg_cost_per_admin"],
                "drug": ndc_rec["drug"],
                "manufacturer": ndc_rec["manufacturer"],
                "rebate_pct": ndc_rec["rebate_pct"],
            }

    # IRA drug name (lowered) -> IRA dict
    _ira_name_index = {}
    for ira in IRA_SELECTED_DRUGS:
        _ira_name_index[ira["drug_name"].lower()] = ira
        _ira_name_index[ira["generic_name"].lower()] = ira


def _tokenize(name: str) -> List[str]:
    """Split a drug name into searchable lowercase tokens."""
    cleaned = re.sub(r"[^a-zA-Z0-9/]", " ", name)
    return [t.lower() for t in cleaned.split() if len(t) >= 3]


def _match_score(query_lower: str, drug_name: str) -> int:
    """Score how well a query matches a drug name. Higher = better match."""
    name_lower = drug_name.lower()
    if query_lower == name_lower:
        return 100
    if name_lower.startswith(query_lower):
        return 90
    if query_lower in name_lower:
        return 70
    # Token match
    query_tokens = set(query_lower.split())
    name_tokens = set(_tokenize(drug_name))
    overlap = query_tokens & name_tokens
    if overlap:
        return 50 + len(overlap) * 10
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_drug(query: str) -> dict:
    """
    Search for a drug by name across all available data sources.

    Returns consolidated results from the synthetic drug list, NADAC pricing,
    NDC/J-code crosswalks, and IRA selected drugs.
    """
    _ensure_indexes()

    query_clean = query.strip()
    query_lower = query_clean.lower()

    if not query_clean or len(query_clean) < 2:
        return {"query": query, "results": [], "result_count": 0}

    results: List[Dict[str, Any]] = []
    seen_ndcs: set = set()

    # 1. Search synthetic DRUGS list
    query_tokens = set(_tokenize(query_clean))
    matched_drugs: List[Dict] = []

    for token in query_tokens:
        for drug in _drug_name_index.get(token, []):
            if drug["ndc"] not in seen_ndcs:
                score = _match_score(query_lower, drug["name"])
                if score > 0:
                    matched_drugs.append((score, drug))
                    seen_ndcs.add(drug["ndc"])

    # Also do a substring search across all drugs
    for drug in DRUGS:
        if drug["ndc"] not in seen_ndcs:
            score = _match_score(query_lower, drug["name"])
            if score > 0:
                matched_drugs.append((score, drug))
                seen_ndcs.add(drug["ndc"])

    # Sort by match score descending
    matched_drugs.sort(key=lambda x: x[0], reverse=True)

    for _score, drug in matched_drugs:
        entry = _build_drug_result(drug)
        results.append(entry)

    # 2. Search J-code crosswalk by drug name
    for jcode_entry in JCODE_CROSSWALK:
        if query_lower in jcode_entry["jcode_desc"].lower():
            for ndc_rec in jcode_entry["ndcs"]:
                if ndc_rec["ndc"] not in seen_ndcs:
                    results.append({
                        "drug_name": ndc_rec["drug"],
                        "ndc": ndc_rec["ndc"],
                        "generic": False,
                        "therapeutic_class": jcode_entry["therapy_class"],
                        "jcode": jcode_entry["jcode"],
                        "jcode_desc": jcode_entry["jcode_desc"],
                        "manufacturer": ndc_rec["manufacturer"],
                        "rebate_estimate_pct": ndc_rec["rebate_pct"],
                        "avg_cost_per_admin": jcode_entry["avg_cost_per_admin"],
                        "source": "jcode_crosswalk",
                        "ira_status": None,
                    })
                    seen_ndcs.add(ndc_rec["ndc"])

    # 3. Check IRA selected drugs
    for ira in IRA_SELECTED_DRUGS:
        if (query_lower in ira["drug_name"].lower()
                or query_lower in ira["generic_name"].lower()):
            # Add if not already present via other sources
            already = any(
                r.get("drug_name", "").lower().startswith(ira["drug_name"].lower())
                for r in results
            )
            if not already:
                results.append({
                    "drug_name": ira["drug_name"],
                    "generic_name": ira["generic_name"],
                    "ndc": None,
                    "generic": False,
                    "therapeutic_class": None,
                    "manufacturer": ira["manufacturer"],
                    "condition": ira["condition"],
                    "current_list_price_30day": ira["current_list_price_30day"],
                    "negotiated_max_fair_price_30day": ira["negotiated_max_fair_price_30day"],
                    "ira_status": "selected_for_negotiation",
                    "source": "ira_selected_drugs",
                })
            else:
                # Annotate existing results with IRA info
                for r in results:
                    if r.get("drug_name", "").lower().startswith(ira["drug_name"].lower()):
                        r["ira_status"] = "selected_for_negotiation"
                        r["negotiated_max_fair_price_30day"] = ira["negotiated_max_fair_price_30day"]

    # 4. Try NADAC search (async, best effort)
    try:
        nadac_results = await nadac_service.search_drugs(query_clean)
        nadac_hits = [r for r in nadac_results if not r.get("error")]
        for nr in nadac_hits[:5]:
            if nr.get("ndc") and nr["ndc"] not in seen_ndcs:
                results.append({
                    "drug_name": nr.get("drug_name", ""),
                    "ndc": nr["ndc"],
                    "generic": None,
                    "therapeutic_class": None,
                    "nadac_per_unit": nr.get("nadac_per_unit"),
                    "nadac_effective_date": nr.get("effective_date"),
                    "source": "nadac",
                    "ira_status": None,
                })
                seen_ndcs.add(nr["ndc"])
    except Exception as e:
        logger.warning("NADAC search failed during drug lookup: %s", e)

    # 5. Enrich results with CMS Medicare spending data
    try:
        cms_hit = cms_spending_service.get_drug_spending(query_clean)
        if cms_hit.get("found"):
            # Annotate existing results with Medicare spending data
            for r in results:
                r_name = r.get("drug_name", "").lower()
                if (query_lower in r_name
                        or r_name.startswith(cms_hit.get("brand_name", "").lower().split()[0])
                        or r_name.startswith(cms_hit.get("generic_name", "").lower().split()[0])):
                    r["cms_medicare_spending"] = {
                        "total_spending": cms_hit["medicare_total_spending"],
                        "total_claims": cms_hit["medicare_total_claims"],
                        "avg_cost_per_claim": cms_hit["medicare_avg_cost_per_claim"],
                        "total_beneficiaries": cms_hit["medicare_total_beneficiaries"],
                        "data_source": cms_hit["data_source"],
                    }
            # If no existing result was annotated, add a standalone CMS entry
            if not any(r.get("cms_medicare_spending") for r in results):
                results.append({
                    "drug_name": cms_hit["brand_name"],
                    "generic_name": cms_hit["generic_name"],
                    "ndc": None,
                    "generic": None,
                    "therapeutic_class": None,
                    "source": "cms_partd_spending",
                    "ira_status": None,
                    "cms_medicare_spending": {
                        "total_spending": cms_hit["medicare_total_spending"],
                        "total_claims": cms_hit["medicare_total_claims"],
                        "avg_cost_per_claim": cms_hit["medicare_avg_cost_per_claim"],
                        "total_beneficiaries": cms_hit["medicare_total_beneficiaries"],
                        "data_source": cms_hit["data_source"],
                    },
                })
    except Exception as e:
        logger.warning("CMS spending lookup failed during drug search: %s", e)

    return {
        "query": query,
        "results": results,
        "result_count": len(results),
        "sources_searched": [
            "clearscript_drug_list",
            "jcode_crosswalk",
            "ira_selected_drugs",
            "cms_nadac",
            "cms_partd_spending",
        ],
    }


async def get_drug_profile(ndc: str) -> dict:
    """
    Full profile for a single NDC including pricing, rebate estimates,
    therapeutic alternatives, and formulary coverage context.
    """
    _ensure_indexes()

    clean_ndc = ndc.replace("-", "").strip()

    profile: Dict[str, Any] = {
        "ndc": clean_ndc,
        "found": False,
    }

    # Check synthetic drug list
    drug = _ndc_index.get(clean_ndc)
    if drug:
        profile.update({
            "found": True,
            "drug_name": drug["name"],
            "generic": drug["generic"],
            "therapeutic_class": drug["class"],
            "nadac_unit": drug["nadac_unit"],
            "awp_unit": drug["awp_unit"],
            "rebate_estimate_pct": drug.get("rebate_pct"),
            "is_specialty": drug.get("specialty", False),
            "generic_alternative": drug.get("generic_alt"),
        })

    # Check J-code crosswalk
    jcode_info = _jcode_ndc_index.get(clean_ndc)
    if jcode_info:
        profile["found"] = True
        profile["jcode"] = jcode_info["jcode"]
        profile["jcode_desc"] = jcode_info["jcode_desc"]
        profile["jcode_therapy_class"] = jcode_info["therapy_class"]
        profile["jcode_avg_cost_per_admin"] = jcode_info["avg_cost_per_admin"]
        profile["jcode_manufacturer"] = jcode_info["manufacturer"]
        profile["jcode_rebate_pct"] = jcode_info["rebate_pct"]

    # Check IRA status
    drug_name = profile.get("drug_name", "")
    ira_match = _ira_name_index.get(drug_name.split()[0].lower() if drug_name else "")
    if ira_match:
        profile["ira_status"] = "selected_for_negotiation"
        profile["ira_drug_name"] = ira_match["drug_name"]
        profile["ira_negotiated_price_30day"] = ira_match["negotiated_max_fair_price_30day"]
        profile["ira_current_list_price_30day"] = ira_match["current_list_price_30day"]
        profile["ira_savings_pct"] = ira_match["savings_pct"]
    else:
        profile["ira_status"] = None

    # Fetch live NADAC pricing
    try:
        nadac_data = await nadac_service.get_price_by_ndc(clean_ndc)
        if not nadac_data.get("error"):
            profile["nadac_live"] = {
                "nadac_per_unit": nadac_data.get("nadac_per_unit"),
                "effective_date": nadac_data.get("effective_date"),
                "pricing_unit": nadac_data.get("pricing_unit"),
                "source": "CMS NADAC API",
            }
    except Exception as e:
        logger.warning("NADAC fetch failed for NDC %s: %s", clean_ndc, e)

    # Find therapeutic alternatives
    if drug:
        alternatives = []
        for d in DRUGS:
            if (d["class"] == drug["class"]
                    and d["ndc"] != clean_ndc
                    and d["generic"]):
                alternatives.append({
                    "drug_name": d["name"],
                    "ndc": d["ndc"],
                    "nadac_unit": d["nadac_unit"],
                    "awp_unit": d["awp_unit"],
                })
        profile["therapeutic_alternatives"] = alternatives[:5]
    else:
        profile["therapeutic_alternatives"] = []

    # AWP-to-NADAC spread estimate
    if profile.get("awp_unit") and profile.get("nadac_unit"):
        awp = profile["awp_unit"]
        nadac = profile["nadac_unit"]
        if nadac > 0:
            spread_pct = round((awp - nadac) / awp * 100, 1)
            profile["awp_nadac_spread_pct"] = spread_pct

    return profile


def _build_drug_result(drug: dict) -> Dict[str, Any]:
    """Build a consolidated search result entry from a DRUGS list item."""
    _ensure_indexes()

    entry: Dict[str, Any] = {
        "drug_name": drug["name"],
        "ndc": drug["ndc"],
        "generic": drug["generic"],
        "therapeutic_class": drug["class"],
        "nadac_unit": drug["nadac_unit"],
        "awp_unit": drug["awp_unit"],
        "rebate_estimate_pct": drug.get("rebate_pct"),
        "is_specialty": drug.get("specialty", False),
        "generic_alternative": drug.get("generic_alt"),
        "source": "clearscript_drug_list",
    }

    # Add J-code info if available
    jcode_info = _jcode_ndc_index.get(drug["ndc"])
    if jcode_info:
        entry["jcode"] = jcode_info["jcode"]
        entry["jcode_desc"] = jcode_info["jcode_desc"]

    # Add IRA status if applicable
    base_name = drug["name"].split()[0].lower()
    ira = _ira_name_index.get(base_name)
    if ira:
        entry["ira_status"] = "selected_for_negotiation"
        entry["negotiated_max_fair_price_30day"] = ira["negotiated_max_fair_price_30day"]
    else:
        entry["ira_status"] = None

    return entry

"""
Batch Cigna formulary processor — infer metadata from filenames, build searchable
cross-plan indices, and compare formulary coverage by state and plan family.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("clearscript.batch_formulary_service")

# ---------------------------------------------------------------------------
# State codes recognized in Cigna filenames
# ---------------------------------------------------------------------------
STATE_CODES = {
    "TX", "CA", "IL", "FL", "IN", "VA", "CO", "AZ", "MS", "NC", "TN", "GA",
}

# Lowercase prefix -> state mapping used in filenames like "ca-advantage-..."
_STATE_PREFIXES = {s.lower(): s for s in STATE_CODES}

# Plan family keywords in order of specificity (longest match first)
_PLAN_FAMILIES = [
    ("national preferred", "National Preferred"),
    ("national-preferred", "National Preferred"),
    ("legacy performance", "Legacy Performance"),
    ("legacy-performance", "Legacy Performance"),
    ("performance", "Performance"),
    ("advantage", "Advantage"),
    ("standard", "Standard"),
    ("premiere", "Premiere"),
    ("essential", "Essential"),
    ("legacy", "Legacy"),
    ("value", "Value"),
    ("plus", "Plus"),
]

# California regulatory variant suffixes
_CA_VARIANTS = {"cdi", "dhmc", "doi", "hmo"}


# ---------------------------------------------------------------------------
# 1. Metadata inference
# ---------------------------------------------------------------------------

def infer_metadata_from_filename(filename: str) -> dict:
    """
    Extract carrier, state, tier_model, plan_family, year, and is_california
    from a Cigna formulary PDF filename.

    Handles patterns such as:
      - advantage-3-tier.pdf.pdf
      - ca-advantage-3-tier-cdi.pdf
      - m-26-rx-tx-989885-cigna-rx-plus-4-tier-pdl.pdf.pdf
      - standard-4-tier-spec.pdf.pdf
      - legacy-performance-3-tier.pdf.pdf
    """
    # Normalize: lowercase, strip extension(s), replace underscores with hyphens
    base = filename.lower()
    # Strip all trailing .pdf extensions
    while base.endswith(".pdf"):
        base = base[:-4]
    base = base.replace("_", "-")

    carrier = "Cigna"

    # --- State ---
    state: Optional[str] = None

    # Pattern 1: 2-letter prefix at start  e.g. "ca-advantage..."
    prefix_match = re.match(r"^([a-z]{2})-", base)
    if prefix_match and prefix_match.group(1).upper() in STATE_CODES:
        state = prefix_match.group(1).upper()

    # Pattern 2: state code embedded like "-tx-" in longer filenames
    if state is None:
        for code in STATE_CODES:
            if re.search(rf"(?:^|[-\s]){code.lower()}(?:[-\s]|$)", base):
                state = code
                break

    is_california = state == "CA"

    # --- Tier model ---
    tier_model: Optional[int] = None
    tier_match = re.search(r"(\d)-tier", base)
    if tier_match:
        t = int(tier_match.group(1))
        if t in (3, 4, 5, 6):
            tier_model = t

    # --- Plan family ---
    plan_family: Optional[str] = None
    for keyword, family_name in _PLAN_FAMILIES:
        if keyword in base:
            plan_family = family_name
            break

    # --- Year ---
    year: int = 2026  # default
    # Look for 4-digit year
    year_match = re.search(r"(20\d{2})", base)
    if year_match:
        year = int(year_match.group(1))
    else:
        # Look for 2-digit year prefix like "m-26-rx-..."
        short_year_match = re.search(r"(?:^|[-\s])(\d{2})(?:[-\s])", base)
        if short_year_match:
            y = int(short_year_match.group(1))
            if 20 <= y <= 35:
                year = 2000 + y

    # --- California regulatory variants ---
    ca_variant: Optional[str] = None
    if is_california:
        for variant in _CA_VARIANTS:
            if variant in base:
                ca_variant = variant.upper()
                break

    return {
        "carrier": carrier,
        "state": state,
        "tier_model": tier_model,
        "plan_family": plan_family,
        "year": year,
        "is_california": is_california,
        "ca_variant": ca_variant,
        "source_filename": filename,
    }


# ---------------------------------------------------------------------------
# 2. Index builder
# ---------------------------------------------------------------------------

def build_formulary_index(parsed_formularies: list[dict]) -> dict:
    """
    Given a list of parsed formularies (each with 'metadata' dict and 'rows'
    list of drug dicts), build a searchable cross-plan index.

    Returns:
        {
            drug_index:  {DRUG_NAME: [{plan, state, tier, tier_band, pa, ql, st, economic_score}, ...]},
            plan_index:  {plan_label: {drug_count, tier_distribution, um_rates, states}},
            state_index: {state: {plans: [...], avg_tier, avg_pa_rate}},
            total_formularies: int,
            total_drugs: int,
        }
    """
    drug_index: dict[str, list[dict]] = {}
    plan_index: dict[str, dict] = {}
    state_index: dict[str, dict] = {}

    for formulary in parsed_formularies:
        meta = formulary.get("metadata", {})
        rows = formulary.get("rows", [])
        plan_label = _plan_label(meta)
        state = meta.get("state") or "National"

        # --- Plan-level aggregation ---
        tiers = [r.get("tier", 0) for r in rows]
        tier_dist: dict[int, int] = {}
        for t in tiers:
            tier_dist[t] = tier_dist.get(t, 0) + 1

        pa_count = sum(1 for r in rows if r.get("pa"))
        ql_count = sum(1 for r in rows if r.get("ql"))
        st_count = sum(1 for r in rows if r.get("st"))
        n = max(len(rows), 1)

        plan_index[plan_label] = {
            "drug_count": len(rows),
            "tier_distribution": tier_dist,
            "um_rates": {
                "pa_pct": round(pa_count / n * 100, 2),
                "ql_pct": round(ql_count / n * 100, 2),
                "st_pct": round(st_count / n * 100, 2),
            },
            "states": [state],
            "metadata": meta,
        }

        # --- State-level aggregation ---
        if state not in state_index:
            state_index[state] = {"plans": [], "all_tiers": [], "pa_flags": []}
        state_index[state]["plans"].append(plan_label)
        state_index[state]["all_tiers"].extend(tiers)
        state_index[state]["pa_flags"].extend([r.get("pa", 0) for r in rows])

        # --- Drug-level index ---
        for row in rows:
            drug_key = row.get("drug_name", "").upper().strip()
            if not drug_key:
                continue
            entry = {
                "plan": plan_label,
                "state": state,
                "tier": row.get("tier"),
                "tier_band": row.get("tier_band"),
                "pa": row.get("pa", 0),
                "ql": row.get("ql", 0),
                "st": row.get("st", 0),
                "economic_score": row.get("economic_score"),
            }
            drug_index.setdefault(drug_key, []).append(entry)

    # Finalize state_index stats
    for state, data in state_index.items():
        all_tiers = data.pop("all_tiers")
        pa_flags = data.pop("pa_flags")
        data["avg_tier"] = round(sum(all_tiers) / max(len(all_tiers), 1), 2)
        data["avg_pa_rate"] = round(
            sum(pa_flags) / max(len(pa_flags), 1) * 100, 2
        )

    return {
        "drug_index": drug_index,
        "plan_index": plan_index,
        "state_index": state_index,
        "total_formularies": len(parsed_formularies),
        "total_drugs": len(drug_index),
    }


# ---------------------------------------------------------------------------
# 3. Drug search
# ---------------------------------------------------------------------------

def search_drug_across_plans(drug_name: str, index: dict) -> dict:
    """
    Search for a drug across all indexed formularies.

    Returns match details, tier range, PA rate, and most/least favorable plans.
    """
    drug_index = index.get("drug_index", {})
    key = drug_name.upper().strip()

    # Exact match first, then substring
    matches = drug_index.get(key, [])
    if not matches:
        for dk, entries in drug_index.items():
            if key in dk or dk in key:
                matches = entries
                key = dk
                break

    if not matches:
        return {
            "drug_name": drug_name,
            "found": False,
            "found_in_plans": [],
            "tier_range": None,
            "pa_rate": 0.0,
            "most_favorable_plan": None,
            "least_favorable_plan": None,
        }

    tiers = [m["tier"] for m in matches if m.get("tier") is not None]
    pa_count = sum(1 for m in matches if m.get("pa"))

    sorted_by_tier = sorted(matches, key=lambda m: m.get("tier") or 99)
    most_favorable = sorted_by_tier[0] if sorted_by_tier else None
    least_favorable = sorted_by_tier[-1] if sorted_by_tier else None

    return {
        "drug_name": key,
        "found": True,
        "found_in_plans": matches,
        "plan_count": len(matches),
        "tier_range": {
            "min": min(tiers) if tiers else None,
            "max": max(tiers) if tiers else None,
        },
        "pa_rate": round(pa_count / max(len(matches), 1) * 100, 2),
        "most_favorable_plan": most_favorable,
        "least_favorable_plan": least_favorable,
    }


# ---------------------------------------------------------------------------
# 4. State comparison
# ---------------------------------------------------------------------------

def get_state_comparison(index: dict) -> dict:
    """
    Compare formulary restrictiveness by state.

    Returns per-state metrics and a ranking by restrictiveness (higher = more
    restrictive, based on avg tier + PA rate).
    """
    state_index = index.get("state_index", {})
    plan_index = index.get("plan_index", {})

    states: list[dict] = []
    for state, data in state_index.items():
        # Compute QL and ST rates from plans in this state
        ql_total = 0
        st_total = 0
        drug_total = 0
        for plan_label in data.get("plans", []):
            pinfo = plan_index.get(plan_label, {})
            dc = pinfo.get("drug_count", 0)
            drug_total += dc
            um = pinfo.get("um_rates", {})
            ql_total += um.get("ql_pct", 0) * dc / 100
            st_total += um.get("st_pct", 0) * dc / 100

        n = max(drug_total, 1)
        avg_tier = data.get("avg_tier", 0)
        pa_rate = data.get("avg_pa_rate", 0)
        ql_rate = round(ql_total / n * 100, 2)
        st_rate = round(st_total / n * 100, 2)

        # Composite restrictiveness score: weighted blend
        restrictiveness = round(avg_tier * 15 + pa_rate * 0.4 + ql_rate * 0.2 + st_rate * 0.2, 2)

        states.append({
            "state": state,
            "plan_count": len(data.get("plans", [])),
            "avg_tier": avg_tier,
            "pa_rate": pa_rate,
            "ql_rate": ql_rate,
            "st_rate": st_rate,
            "drug_count": drug_total,
            "restrictiveness_score": restrictiveness,
        })

    # Rank by restrictiveness descending
    states.sort(key=lambda s: s["restrictiveness_score"], reverse=True)
    for rank, s in enumerate(states, 1):
        s["rank"] = rank

    return {
        "states": states,
        "most_restrictive": states[0]["state"] if states else None,
        "least_restrictive": states[-1]["state"] if states else None,
    }


# ---------------------------------------------------------------------------
# Mock / demo data
# ---------------------------------------------------------------------------

def get_mock_index() -> dict:
    """Return a pre-built demo index for testing without real PDF uploads."""
    mock_formularies = [
        {
            "metadata": infer_metadata_from_filename("advantage-3-tier.pdf.pdf"),
            "rows": _mock_rows(tier_model=3, state=None, plan="Advantage 3-Tier"),
        },
        {
            "metadata": infer_metadata_from_filename("ca-advantage-3-tier-cdi.pdf"),
            "rows": _mock_rows(tier_model=3, state="CA", plan="CA Advantage 3-Tier CDI"),
        },
        {
            "metadata": infer_metadata_from_filename("m-26-rx-tx-989885-cigna-rx-plus-4-tier-pdl.pdf.pdf"),
            "rows": _mock_rows(tier_model=4, state="TX", plan="TX Plus 4-Tier"),
        },
        {
            "metadata": infer_metadata_from_filename("standard-4-tier-spec.pdf.pdf"),
            "rows": _mock_rows(tier_model=4, state=None, plan="Standard 4-Tier"),
        },
        {
            "metadata": infer_metadata_from_filename("fl-value-3-tier.pdf"),
            "rows": _mock_rows(tier_model=3, state="FL", plan="FL Value 3-Tier"),
        },
    ]
    return build_formulary_index(mock_formularies)


def _mock_rows(tier_model: int, state: Optional[str], plan: str) -> list[dict]:
    """TEST-ONLY: Generate mock drug rows for demo/test purposes. Not called by production endpoints."""
    import random
    random.seed(hash(plan) % 2**31)

    _SAMPLE_DRUGS = [
        "ATORVASTATIN", "METFORMIN", "LISINOPRIL", "AMLODIPINE", "OMEPRAZOLE",
        "SIMVASTATIN", "LOSARTAN", "GABAPENTIN", "HYDROCHLOROTHIAZIDE", "SERTRALINE",
        "HUMIRA", "STELARA", "DUPIXENT", "KEYTRUDA", "OZEMPIC",
        "JARDIANCE", "ELIQUIS", "XARELTO", "TRULICITY", "ENTRESTO",
        "SKYRIZI", "RINVOQ", "TREMFYA", "COSENTYX", "OTEZLA",
        "REVLIMID", "IMBRUVICA", "IBRANCE", "TAGRISSO", "XTANDI",
    ]

    from services.formulary_service import TIER_MAPS
    tier_map = TIER_MAPS.get(tier_model, TIER_MAPS[4])
    max_tier = max(tier_map.keys())

    rows = []
    for drug in _SAMPLE_DRUGS:
        tier = random.randint(1, max_tier)
        band, score = tier_map.get(tier, ("unknown", 2.0))
        pa = 1 if random.random() < 0.25 else 0
        ql = 1 if random.random() < 0.15 else 0
        st = 1 if random.random() < 0.10 else 0
        rows.append({
            "drug_name": drug,
            "tier": tier,
            "tier_band": band,
            "economic_score": score,
            "pa": pa,
            "ql": ql,
            "st": st,
        })
    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan_label(meta: dict) -> str:
    """Build a human-readable plan label from metadata."""
    parts = []
    if meta.get("state"):
        parts.append(meta["state"])
    if meta.get("plan_family"):
        parts.append(meta["plan_family"])
    if meta.get("tier_model"):
        parts.append(f"{meta['tier_model']}-Tier")
    if meta.get("ca_variant"):
        parts.append(meta["ca_variant"])
    if meta.get("year") and meta["year"] != 2026:
        parts.append(str(meta["year"]))
    return " ".join(parts) if parts else meta.get("source_filename", "Unknown Plan")

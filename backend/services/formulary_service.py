"""
Formulary PDF parsing, scoring, and comparison service.

Extracts structured drug data from PBM formulary PDFs (Cigna/ESI/generic),
normalizes tier models, scores formularies on cost/access/specialty dimensions,
and compares two formularies side-by-side.
"""

from __future__ import annotations

import io
import re
import logging
from typing import Optional

import pdfplumber

logger = logging.getLogger("clearscript.formulary_service")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UM_FLAGS = ("PA", "QL", "ST", "SRX", "LDD", "AGE")

# Tier normalization maps: tier_model -> {tier_int: (tier_band, economic_score)}
TIER_MAPS: dict[int, dict[int, tuple[str, float]]] = {
    3: {
        1: ("generic", 1.0),
        2: ("preferred_brand", 2.0),
        3: ("nonpreferred_brand", 3.0),
    },
    4: {
        1: ("generic", 1.2),
        2: ("preferred_brand", 2.0),
        3: ("nonpreferred_brand", 3.0),
        4: ("specialty", 5.0),
    },
    5: {
        1: ("preferred_generic", 1.0),
        2: ("generic", 1.2),
        3: ("preferred_brand", 2.0),
        4: ("nonpreferred_brand", 3.0),
        5: ("specialty", 5.0),
    },
    6: {
        1: ("preferred_generic", 1.0),
        2: ("generic", 1.2),
        3: ("preferred_brand", 2.0),
        4: ("nonpreferred_brand", 3.0),
        5: ("nonpreferred_brand_high", 4.0),
        6: ("specialty", 5.0),
    },
}

# Header values to skip when parsing table rows
_HEADER_VALUES = frozenset({
    "medication name", "drug name", "drug", "medication", "name",
    "tier", "notes", "requirements/limits", "requirements / limits",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_text(value: object) -> str:
    """Convert a table cell to clean single-line text."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text.strip()


def _parse_notes(notes_raw: str) -> dict:
    """Extract UM flags from a notes/requirements cell."""
    notes = _clean_text(notes_raw).upper()
    tokens = [t.strip() for t in notes.split(",") if t.strip()] if notes else []
    return {
        "notes": notes,
        "notes_tokens": "|".join(tokens),
        "pa": int("PA" in tokens),
        "ql": int("QL" in tokens),
        "st": int("ST" in tokens),
        "srx": int("SRX" in tokens),
        "ldd": int("LDD" in tokens),
        "age": int("AGE" in tokens),
    }


def _detect_tier_model(tiers: list[int]) -> int:
    """Infer the tier model from the set of observed tier values."""
    if not tiers:
        return 4  # sensible default
    max_tier = max(tiers)
    if max_tier <= 3:
        return 3
    elif max_tier == 4:
        return 4
    elif max_tier == 5:
        return 5
    else:
        return 6


def _normalize_tier(tier_int: int, tier_model: int) -> tuple[str, Optional[float]]:
    """Return (tier_band, economic_score) for a given tier and model."""
    mapping = TIER_MAPS.get(tier_model, {})
    if tier_int in mapping:
        return mapping[tier_int]
    return ("unknown", None)


def _is_header_row(cells: list[str]) -> bool:
    """Return True if this table row looks like a header."""
    return any(c.lower() in _HEADER_VALUES for c in cells if c)


def _mean(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _rate(flags: list[int]) -> float:
    """Proportion of 1s in a binary flag list."""
    if not flags:
        return 0.0
    return sum(flags) / len(flags)


def _clamp_100(x: float) -> float:
    return round(max(0.0, min(100.0, x)), 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_formulary_pdf(
    content: bytes,
    tier_model: int | None = None,
    filename: str = "upload.pdf",
) -> list[dict]:
    """
    Parse a PBM formulary PDF into structured row dicts.

    Parameters
    ----------
    content : bytes
        Raw PDF file bytes.
    tier_model : int, optional
        Force a specific tier model (3/4/5/6). If None, the model is
        auto-detected from the maximum observed tier number.
    filename : str
        Original filename, used for row_id generation.

    Returns
    -------
    list[dict]
        One dict per drug row with keys: drug_name, tier, tier_band,
        economic_score, pa, ql, st, srx, ldd, age, specialty_proxy, etc.
    """
    rows: list[dict] = []
    observed_tiers: list[int] = []

    # First pass: extract raw rows and collect tier values for auto-detection
    raw_entries: list[dict] = []

    try:
        pdf_file = io.BytesIO(content)
        with pdfplumber.open(pdf_file) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    for row in table:
                        if not row or len(row) < 2:
                            continue

                        cells = [_clean_text(c) for c in row]
                        if _is_header_row(cells):
                            continue

                        drug = cells[0]
                        tier_str = cells[1] if len(cells) > 1 else ""
                        notes_raw = cells[2] if len(cells) > 2 else ""

                        if not drug or len(drug) < 3:
                            continue
                        if not tier_str.isdigit():
                            continue

                        tier_int = int(tier_str)
                        observed_tiers.append(tier_int)
                        raw_entries.append({
                            "drug": drug,
                            "tier_int": tier_int,
                            "notes_raw": notes_raw,
                            "page": page_number,
                        })
    except Exception:
        logger.exception("Failed to parse formulary PDF")
        raise ValueError("Could not parse the uploaded PDF. Ensure it is a valid formulary PDF.")

    if not raw_entries:
        return []

    # Resolve tier model
    effective_model = tier_model if tier_model in (3, 4, 5, 6) else _detect_tier_model(observed_tiers)

    # Second pass: build structured rows with normalization
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    for idx, entry in enumerate(raw_entries):
        tier_band, economic_score = _normalize_tier(entry["tier_int"], effective_model)
        notes_info = _parse_notes(entry["notes_raw"])

        rows.append({
            "row_id": f"{stem}_{entry['page']}_{idx}",
            "drug_name": entry["drug"].upper(),
            "drug_name_display": entry["drug"],
            "tier": entry["tier_int"],
            "tier_band": tier_band,
            "economic_score": economic_score,
            **notes_info,
            "specialty_proxy": int(
                notes_info["srx"] == 1
                or notes_info["ldd"] == 1
                or entry["tier_int"] >= 4
            ),
            "tier_model": effective_model,
            "page": entry["page"],
        })

    logger.info(
        "Parsed %d drugs from %s (tier_model=%d)",
        len(rows), filename, effective_model,
    )
    return rows


def score_formulary(rows: list[dict]) -> dict:
    """
    Score a parsed formulary on three dimensions.

    Returns a dict with cost_segmentation_score, access_restriction_score,
    specialty_intensity_score, plus underlying rate breakdowns.
    """
    if not rows:
        return {
            "total_drugs": 0,
            "tier_model": None,
            "weighted_tier_avg": 0.0,
            "tier1_share_pct": 0.0,
            "tier4plus_share_pct": 0.0,
            "pa_pct": 0.0,
            "ql_pct": 0.0,
            "st_pct": 0.0,
            "srx_pct": 0.0,
            "ldd_pct": 0.0,
            "age_pct": 0.0,
            "cost_segmentation_score": 0.0,
            "access_restriction_score": 0.0,
            "specialty_intensity_score": 0.0,
        }

    tiers = [r["tier"] for r in rows]
    weighted_tier_avg = _mean(tiers)
    tier1_share = _rate([1 if t == 1 else 0 for t in tiers])
    tier4plus_share = _rate([1 if t >= 4 else 0 for t in tiers])

    pa_rate = _rate([r["pa"] for r in rows])
    ql_rate = _rate([r["ql"] for r in rows])
    st_rate = _rate([r["st"] for r in rows])
    srx_rate = _rate([r["srx"] for r in rows])
    ldd_rate = _rate([r["ldd"] for r in rows])
    age_rate = _rate([r["age"] for r in rows])

    cost_score = _clamp_100(
        (weighted_tier_avg * 20)
        + (tier4plus_share * 40)
        + ((1 - tier1_share) * 20)
    )

    access_score = _clamp_100(
        (pa_rate * 35)
        + (ql_rate * 20)
        + (st_rate * 25)
        + (ldd_rate * 10)
        + (age_rate * 10)
    )

    specialty_score = _clamp_100(
        (srx_rate * 50)
        + (ldd_rate * 20)
        + (tier4plus_share * 30)
    )

    return {
        "total_drugs": len(rows),
        "tier_model": rows[0].get("tier_model"),
        "weighted_tier_avg": round(weighted_tier_avg, 4),
        "tier1_share_pct": round(tier1_share * 100, 2),
        "tier4plus_share_pct": round(tier4plus_share * 100, 2),
        "pa_pct": round(pa_rate * 100, 2),
        "ql_pct": round(ql_rate * 100, 2),
        "st_pct": round(st_rate * 100, 2),
        "srx_pct": round(srx_rate * 100, 2),
        "ldd_pct": round(ldd_rate * 100, 2),
        "age_pct": round(age_rate * 100, 2),
        "cost_segmentation_score": cost_score,
        "access_restriction_score": access_score,
        "specialty_intensity_score": specialty_score,
    }


def compare_formularies(
    rows_a: list[dict],
    rows_b: list[dict],
    label_a: str = "Formulary A",
    label_b: str = "Formulary B",
) -> dict:
    """
    Compare two parsed formularies.

    Returns scoring for each, deltas, tier change details,
    drugs added/removed, and a human-readable interpretation.
    """
    score_a = score_formulary(rows_a)
    score_b = score_formulary(rows_b)

    # Build drug lookup dicts keyed on normalized name
    def _drug_key(name: str) -> str:
        return re.sub(r"\s+", " ", name.upper().strip())

    lookup_a: dict[str, dict] = {}
    for r in rows_a:
        key = _drug_key(r["drug_name"])
        lookup_a[key] = r

    lookup_b: dict[str, dict] = {}
    for r in rows_b:
        key = _drug_key(r["drug_name"])
        lookup_b[key] = r

    keys_a = set(lookup_a.keys())
    keys_b = set(lookup_b.keys())

    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)
    common = sorted(keys_a & keys_b)

    # Tier changes for drugs present in both
    tier_changes: list[dict] = []
    um_changes: list[dict] = []

    for key in common:
        ra = lookup_a[key]
        rb = lookup_b[key]

        if ra["tier"] != rb["tier"]:
            tier_changes.append({
                "drug_name": rb["drug_name"],
                "tier_a": ra["tier"],
                "tier_b": rb["tier"],
                "tier_band_a": ra.get("tier_band", "unknown"),
                "tier_band_b": rb.get("tier_band", "unknown"),
                "direction": "up" if rb["tier"] > ra["tier"] else "down",
            })

        # Check for UM flag changes
        flags_changed = {}
        for flag in ("pa", "ql", "st", "srx", "ldd", "age"):
            if ra.get(flag, 0) != rb.get(flag, 0):
                flags_changed[flag] = {"a": ra.get(flag, 0), "b": rb.get(flag, 0)}
        if flags_changed:
            um_changes.append({
                "drug_name": rb["drug_name"],
                "changes": flags_changed,
            })

    # Score deltas
    cost_delta = round(score_b["cost_segmentation_score"] - score_a["cost_segmentation_score"], 2)
    access_delta = round(score_b["access_restriction_score"] - score_a["access_restriction_score"], 2)
    specialty_delta = round(score_b["specialty_intensity_score"] - score_a["specialty_intensity_score"], 2)

    # Human-readable interpretation
    interpretation = _build_interpretation(label_a, label_b, cost_delta, access_delta, specialty_delta)

    return {
        "label_a": label_a,
        "label_b": label_b,
        "score_a": score_a,
        "score_b": score_b,
        "deltas": {
            "cost_segmentation": cost_delta,
            "access_restriction": access_delta,
            "specialty_intensity": specialty_delta,
        },
        "drugs_added": [lookup_b[k]["drug_name"] for k in added],
        "drugs_removed": [lookup_a[k]["drug_name"] for k in removed],
        "drugs_added_count": len(added),
        "drugs_removed_count": len(removed),
        "tier_changes": tier_changes,
        "tier_changes_count": len(tier_changes),
        "um_changes": um_changes,
        "um_changes_count": len(um_changes),
        "common_drugs_count": len(common),
        "interpretation": interpretation,
    }


def _build_interpretation(
    label_a: str,
    label_b: str,
    cost_delta: float,
    access_delta: float,
    specialty_delta: float,
) -> str:
    """Generate a human-readable interpretation of the comparison deltas."""
    lines: list[str] = [
        "Scoring Interpretation",
        "=" * 40,
        "",
        f"{label_a} vs {label_b}: cost delta {cost_delta}, "
        f"access delta {access_delta}, specialty delta {specialty_delta}.",
        "",
    ]

    # Cost segmentation
    if cost_delta >= 15:
        lines.append(
            f"{label_b} is materially more cost-segmented than {label_a}, "
            "indicating greater differentiation of member cost-sharing across the formulary."
        )
    elif cost_delta >= 5:
        lines.append(f"{label_b} is moderately more cost-segmented than {label_a}.")
    elif abs(cost_delta) < 5:
        lines.append("The two formularies have broadly similar cost segmentation.")
    else:
        lines.append(f"{label_b} is less cost-segmented than {label_a}.")

    # Access restriction
    if abs(access_delta) < 2:
        lines.append(
            "Access controls are effectively unchanged; the difference is primarily "
            "financial rather than clinical."
        )
    elif access_delta >= 5:
        lines.append(f"{label_b} applies meaningfully more utilization management than {label_a}.")
    elif access_delta <= -5:
        lines.append(f"{label_b} applies meaningfully less utilization management than {label_a}.")
    else:
        lines.append("Access restriction differences are modest.")

    # Specialty
    if abs(specialty_delta) < 2:
        lines.append("Specialty management appears structurally similar across both formularies.")
    elif specialty_delta >= 5:
        lines.append(f"{label_b} shows higher specialty intensity than {label_a}.")
    elif specialty_delta <= -5:
        lines.append(f"{label_b} shows lower specialty intensity than {label_a}.")
    else:
        lines.append("Specialty intensity differences are modest.")

    return "\n".join(lines)

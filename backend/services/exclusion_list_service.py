"""
Express Scripts / Evernorth National Preferred Formulary Exclusion List
parsing, year-over-year comparison, and claims impact estimation.

Handles ESI exclusion PDFs from 2020, 2022, 2026 (Evernorth-branded)
with 3-column tables: Drug Class | Excluded Medications | Preferred Alternatives.
"""

from __future__ import annotations

import io
import re
import logging
from typing import Optional

import pdfplumber

logger = logging.getLogger("clearscript.exclusion_list_service")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_text(value: object) -> str:
    """Convert a table cell to clean single-line text."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text.strip()


def _normalize_drug_name(name: str) -> str:
    """Normalize a drug name for comparison: uppercase, strip annotations."""
    name = name.upper().strip()
    # Remove common footnote markers and annotations
    name = re.sub(r"[~*†‡§¶#]+$", "", name)
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)  # trailing parenthetical
    name = name.strip(" ,;")
    return name


def _split_medications(cell_text: str) -> list[str]:
    """
    Split a cell containing multiple medication names into individual names.

    ESI PDFs typically list one drug per line. Within a single cell the text
    may be newline-separated or comma-separated. We handle both.
    """
    if not cell_text:
        return []

    # pdfplumber usually joins lines with newlines already collapsed to spaces,
    # but sometimes they survive.  Also handle bullet chars.
    text = cell_text.replace("\u2022", "\n").replace("•", "\n")

    # Split on newlines first
    parts: list[str] = []
    for segment in text.split("\n"):
        segment = segment.strip()
        if not segment:
            continue
        # Some cells use semicolons as separators
        for sub in segment.split(";"):
            sub = sub.strip()
            if sub:
                parts.append(sub)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for p in parts:
        normed = _normalize_drug_name(p)
        if normed and normed not in seen and len(normed) >= 3:
            seen.add(normed)
            result.append(normed)
    return result


_HEADER_KEYWORDS = frozenset({
    "drug class", "excluded medications", "preferred alternatives",
    "excluded medication", "preferred alternative",
    "therapeutic class", "therapeutic category",
    "medications/products", "alternatives",
})

_SKIP_KEYWORDS = frozenset({
    "excluded medications/products at a glance",
    "national preferred formulary exclusions",
    "express scripts", "evernorth health services",
    "page", "effective",
})


def _is_header_row(cells: list[str]) -> bool:
    """Return True if this row looks like a table header."""
    joined = " ".join(cells).lower().strip()
    return any(kw in joined for kw in _HEADER_KEYWORDS)


def _is_skip_row(cells: list[str]) -> bool:
    """Return True for boilerplate / footer rows that should be skipped."""
    joined = " ".join(cells).lower().strip()
    if not joined or len(joined) < 3:
        return True
    # Skip the alphabetical summary section at the end
    if any(kw in joined for kw in _SKIP_KEYWORDS):
        return True
    return False


def _looks_like_class_header(text: str) -> bool:
    """
    Detect drug class headers which are typically ALL CAPS and BOLD.
    Examples: "ANTIINFECTIVES", "CARDIOVASCULAR", "DERMATOLOGY".
    """
    cleaned = text.strip()
    if not cleaned:
        return False
    # Class headers are usually all uppercase, no digits, relatively short
    alpha_only = re.sub(r"[^A-Za-z/ ]", "", cleaned)
    if not alpha_only:
        return False
    return (
        alpha_only == alpha_only.upper()
        and len(alpha_only) >= 4
        and len(alpha_only) <= 60
        and not any(char.isdigit() for char in cleaned)
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_exclusion_pdf(content: bytes) -> list[dict]:
    """
    Parse an Express Scripts / Evernorth exclusion list PDF into structured rows.

    Parameters
    ----------
    content : bytes
        Raw PDF file bytes.

    Returns
    -------
    list[dict]
        Each dict has keys:
        - drug_class (str): e.g. "CARDIOVASCULAR"
        - drug_subclass (str): e.g. "ACE Inhibitors"
        - excluded_medications (list[str]): normalized drug names
        - preferred_alternatives (list[str]): normalized drug names
    """
    rows: list[dict] = []
    current_class: str = ""
    current_subclass: str = ""

    try:
        pdf_file = io.BytesIO(content)
        with pdfplumber.open(pdf_file) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()

                if not tables:
                    # Fall back to extracting text and trying to parse it
                    _parse_text_fallback(page, rows, current_class, current_subclass)
                    continue

                for table in tables:
                    if not table:
                        continue

                    for row in table:
                        if not row or len(row) < 2:
                            continue

                        cells = [_clean_text(c) for c in row]

                        if _is_header_row(cells):
                            continue
                        if _is_skip_row(cells):
                            continue

                        # ESI exclusion PDFs have 3 columns:
                        # Drug Class | Excluded Medications | Preferred Alternatives
                        col_class = cells[0] if len(cells) > 0 else ""
                        col_excluded = cells[1] if len(cells) > 1 else ""
                        col_alternatives = cells[2] if len(cells) > 2 else ""

                        # Update class/subclass tracking
                        if col_class:
                            if _looks_like_class_header(col_class):
                                current_class = col_class.upper().strip()
                                current_subclass = ""
                            else:
                                # It is a subclass like "ACE Inhibitors" or
                                # a continuation row with only class info
                                candidate = col_class.strip()
                                if candidate and not col_excluded:
                                    # Standalone subclass label row
                                    current_subclass = candidate
                                    continue
                                elif candidate:
                                    current_subclass = candidate

                        # Extract drug names from medication and alternative columns
                        excluded = _split_medications(col_excluded)
                        alternatives = _split_medications(col_alternatives)

                        if not excluded:
                            continue

                        rows.append({
                            "drug_class": current_class,
                            "drug_subclass": current_subclass,
                            "excluded_medications": excluded,
                            "preferred_alternatives": alternatives,
                        })

    except Exception:
        logger.exception("Failed to parse exclusion list PDF")
        raise ValueError(
            "Could not parse the uploaded PDF. "
            "Ensure it is a valid Express Scripts / Evernorth exclusion list PDF."
        )

    # Deduplicate rows that may span pages
    rows = _deduplicate_rows(rows)

    logger.info("Parsed %d exclusion rows from PDF", len(rows))
    return rows


def _parse_text_fallback(
    page,
    rows: list[dict],
    current_class: str,
    current_subclass: str,
) -> None:
    """
    Fallback parser for pages where pdfplumber cannot extract tables.
    Attempts line-by-line parsing of the page text.
    """
    text = page.extract_text()
    if not text:
        return

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        lower = line.lower()
        if any(kw in lower for kw in _SKIP_KEYWORDS):
            continue
        if any(kw in lower for kw in _HEADER_KEYWORDS):
            continue

        if _looks_like_class_header(line):
            current_class = line.upper().strip()
            current_subclass = ""
            continue

        # Heuristic: lines with tabs or multiple spaces may be table-like
        parts = re.split(r"\t{1,}|\s{3,}", line)
        if len(parts) >= 2:
            excluded = _split_medications(parts[0] if len(parts) > 0 else "")
            alternatives = _split_medications(parts[1] if len(parts) > 1 else "")
            if excluded:
                rows.append({
                    "drug_class": current_class,
                    "drug_subclass": current_subclass,
                    "excluded_medications": excluded,
                    "preferred_alternatives": alternatives,
                })


def _deduplicate_rows(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate rows that can occur at page boundaries."""
    seen: set[str] = set()
    deduped: list[dict] = []
    for row in rows:
        key = (
            row["drug_class"]
            + "|" + row["drug_subclass"]
            + "|" + ",".join(row["excluded_medications"])
        )
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_exclusion_lists(
    list_a: list[dict],
    list_b: list[dict],
    year_a: str = "Year A",
    year_b: str = "Year B",
) -> dict:
    """
    Compare two parsed exclusion lists year-over-year.

    Parameters
    ----------
    list_a, list_b : list[dict]
        Output of ``parse_exclusion_pdf``.
    year_a, year_b : str
        Labels for each year (e.g. "2022", "2026").

    Returns
    -------
    dict with keys:
        newly_excluded, removed_from_exclusion, alternative_changes,
        class_summary, total_excluded_a, total_excluded_b, churn_rate
    """
    # Build flat sets of excluded drugs for each list, plus a mapping of
    # drug -> preferred alternatives and drug -> class info.
    drugs_a: set[str] = set()
    drugs_b: set[str] = set()
    alt_map_a: dict[str, list[str]] = {}
    alt_map_b: dict[str, list[str]] = {}
    class_map_a: dict[str, str] = {}
    class_map_b: dict[str, str] = {}

    for row in list_a:
        for drug in row["excluded_medications"]:
            drugs_a.add(drug)
            alt_map_a[drug] = row["preferred_alternatives"]
            class_map_a[drug] = row["drug_class"]

    for row in list_b:
        for drug in row["excluded_medications"]:
            drugs_b.add(drug)
            alt_map_b[drug] = row["preferred_alternatives"]
            class_map_b[drug] = row["drug_class"]

    newly_excluded = sorted(drugs_b - drugs_a)
    removed_from_exclusion = sorted(drugs_a - drugs_b)
    common = drugs_a & drugs_b

    # Detect alternative changes for drugs excluded in both years
    alternative_changes: list[dict] = []
    for drug in sorted(common):
        alts_a = set(alt_map_a.get(drug, []))
        alts_b = set(alt_map_b.get(drug, []))
        if alts_a != alts_b:
            alternative_changes.append({
                "drug": drug,
                f"alternatives_{year_a}": sorted(alts_a),
                f"alternatives_{year_b}": sorted(alts_b),
                "added_alternatives": sorted(alts_b - alts_a),
                "removed_alternatives": sorted(alts_a - alts_b),
            })

    # Per-class summary
    all_classes = sorted(
        set(class_map_a.values()) | set(class_map_b.values())
    )
    class_summary: list[dict] = []
    for cls in all_classes:
        cls_drugs_a = {d for d, c in class_map_a.items() if c == cls}
        cls_drugs_b = {d for d, c in class_map_b.items() if c == cls}
        additions = len(cls_drugs_b - cls_drugs_a)
        removals = len(cls_drugs_a - cls_drugs_b)
        class_summary.append({
            "drug_class": cls,
            f"count_{year_a}": len(cls_drugs_a),
            f"count_{year_b}": len(cls_drugs_b),
            "additions": additions,
            "removals": removals,
            "net_change": additions - removals,
        })

    total_a = len(drugs_a)
    total_b = len(drugs_b)
    universe = len(drugs_a | drugs_b)
    churn = len(newly_excluded) + len(removed_from_exclusion)
    churn_rate = round((churn / universe * 100) if universe else 0.0, 2)

    return {
        "year_a": year_a,
        "year_b": year_b,
        "total_excluded_a": total_a,
        "total_excluded_b": total_b,
        "newly_excluded": newly_excluded,
        "newly_excluded_count": len(newly_excluded),
        "removed_from_exclusion": removed_from_exclusion,
        "removed_from_exclusion_count": len(removed_from_exclusion),
        "alternative_changes": alternative_changes,
        "alternative_changes_count": len(alternative_changes),
        "class_summary": class_summary,
        "churn_rate": churn_rate,
        "interpretation": _build_comparison_interpretation(
            year_a, year_b, total_a, total_b,
            len(newly_excluded), len(removed_from_exclusion),
            churn_rate,
        ),
    }


def _build_comparison_interpretation(
    year_a: str,
    year_b: str,
    total_a: int,
    total_b: int,
    added: int,
    removed: int,
    churn_rate: float,
) -> str:
    """Generate a human-readable summary of the comparison."""
    lines = [
        f"Exclusion List Comparison: {year_a} vs {year_b}",
        "=" * 50,
        "",
        f"Total excluded medications: {total_a} ({year_a}) -> {total_b} ({year_b})",
        f"Net change: {total_b - total_a:+d} medications",
        f"Newly excluded: {added}",
        f"Returned to formulary: {removed}",
        f"Churn rate: {churn_rate}%",
        "",
    ]

    if total_b > total_a:
        lines.append(
            f"The {year_b} exclusion list is more restrictive, with {added} new "
            f"medications excluded. Plan members on these drugs will need to "
            f"switch to preferred alternatives or seek exceptions."
        )
    elif total_b < total_a:
        lines.append(
            f"The {year_b} exclusion list is less restrictive, with {removed} "
            f"medications returned to the formulary. This may reflect generic "
            f"availability or competitive market dynamics."
        )
    else:
        lines.append(
            "The total number of exclusions is unchanged, but individual drugs "
            "may have been swapped in or out."
        )

    if churn_rate > 30:
        lines.append(
            "\nHigh churn rate indicates significant formulary volatility. "
            "Employers should carefully review transition protocols and member "
            "communication plans."
        )
    elif churn_rate > 15:
        lines.append(
            "\nModerate churn rate. Review transition processes for affected members."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claims impact estimation
# ---------------------------------------------------------------------------

def estimate_exclusion_impact(
    exclusions: list[dict],
    claims: list[dict],
) -> dict:
    """
    Estimate how many current claims would be affected by the exclusion list
    and the dollar impact of switching to preferred alternatives.

    Parameters
    ----------
    exclusions : list[dict]
        Output of ``parse_exclusion_pdf``.
    claims : list[dict]
        Claims data (from ``data_service.get_claims()``), each with at
        least ``drug_name``, ``plan_paid``, ``nadac_cost``.

    Returns
    -------
    dict with impact metrics.
    """
    # Build a set of excluded drug names and a map to alternatives
    excluded_set: set[str] = set()
    alt_map: dict[str, list[str]] = {}
    class_map: dict[str, str] = {}

    for row in exclusions:
        for drug in row["excluded_medications"]:
            excluded_set.add(drug)
            alt_map[drug] = row["preferred_alternatives"]
            class_map[drug] = row["drug_class"]

    # Match claims against exclusion list
    affected_claims: list[dict] = []
    unaffected_count = 0
    total_affected_spend = 0.0
    total_claims_spend = 0.0

    for claim in claims:
        claim_drug = claim.get("drug_name", "").upper().strip()
        plan_paid = claim.get("plan_paid", 0.0)
        total_claims_spend += plan_paid

        # Check if the claim drug matches any excluded medication
        matched_exclusion: Optional[str] = None
        for excluded in excluded_set:
            # Fuzzy match: check if the excluded drug name is contained in
            # the claim drug name or vice versa (handles brand vs generic
            # name differences, dosage forms, etc.)
            if excluded in claim_drug or claim_drug in excluded:
                matched_exclusion = excluded
                break

        if matched_exclusion:
            nadac_cost = claim.get("nadac_cost", 0.0)
            # Estimate savings: switching to a preferred alternative should
            # bring cost closer to NADAC
            estimated_savings = round(max(0.0, plan_paid - nadac_cost * 1.15), 2)

            affected_claims.append({
                "claim_drug": claim_drug,
                "matched_exclusion": matched_exclusion,
                "drug_class": class_map.get(matched_exclusion, "Unknown"),
                "preferred_alternatives": alt_map.get(matched_exclusion, []),
                "plan_paid": plan_paid,
                "nadac_cost": nadac_cost,
                "estimated_savings": estimated_savings,
            })
            total_affected_spend += plan_paid
        else:
            unaffected_count += 1

    # Aggregate by drug class
    class_impact: dict[str, dict] = {}
    for ac in affected_claims:
        cls = ac["drug_class"]
        if cls not in class_impact:
            class_impact[cls] = {
                "drug_class": cls,
                "affected_claims": 0,
                "total_spend": 0.0,
                "estimated_savings": 0.0,
            }
        class_impact[cls]["affected_claims"] += 1
        class_impact[cls]["total_spend"] += ac["plan_paid"]
        class_impact[cls]["estimated_savings"] += ac["estimated_savings"]

    # Round aggregates
    for v in class_impact.values():
        v["total_spend"] = round(v["total_spend"], 2)
        v["estimated_savings"] = round(v["estimated_savings"], 2)

    total_estimated_savings = round(
        sum(ac["estimated_savings"] for ac in affected_claims), 2
    )

    return {
        "total_claims": len(claims),
        "affected_claims": len(affected_claims),
        "unaffected_claims": unaffected_count,
        "affected_pct": round(
            len(affected_claims) / len(claims) * 100 if claims else 0.0, 2
        ),
        "total_claims_spend": round(total_claims_spend, 2),
        "total_affected_spend": round(total_affected_spend, 2),
        "total_estimated_savings": total_estimated_savings,
        "savings_pct": round(
            total_estimated_savings / total_claims_spend * 100
            if total_claims_spend else 0.0, 2
        ),
        "class_impact": sorted(
            class_impact.values(),
            key=lambda x: x["estimated_savings"],
            reverse=True,
        ),
        "affected_claim_details": affected_claims[:50],  # cap detail output
        "excluded_drugs_checked": len(excluded_set),
    }

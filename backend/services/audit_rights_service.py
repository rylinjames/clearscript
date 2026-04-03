"""
Audit Rights Benchmark Scorer.
Compares uploaded contract's audit rights against gold-standard 11-point state template.
Based on intel from Nick Beckman (Segal) — standard state PBM audit contract language.
"""

# The 11 gold-standard audit confirmations from state PBM contracts
GOLD_STANDARD_AUDIT_RIGHTS = [
    {
        "id": "ndc_level_audit",
        "label": "NDC-Level Electronic Audit",
        "description": "All financial pricing components (discounts, dispensing fees, rebates) subject to independent electronic audit using date-sensitive AWP at NDC level from nationally recognized pricing source (e.g., MediSpan).",
        "keywords": ["ndc", "ndc level", "ndc-level", "medispan", "electronic audit", "awp", "pricing source"],
    },
    {
        "id": "annual_audit_right",
        "label": "Annual Audit Right with Auditor of Choice",
        "description": "Right to audit annually with an auditor of its choice, for both claims and rebates, with full PBM cooperation.",
        "keywords": ["annual", "auditor of", "choice", "yearly audit", "once per year"],
    },
    {
        "id": "lookback_36_months",
        "label": "36-Month Claims Lookback",
        "description": "Right to audit up to 36 months of claims data at no additional charge.",
        "keywords": ["36 month", "36-month", "three year", "3 year", "lookback"],
    },
    {
        "id": "90_day_notice",
        "label": "90-Day Advance Notice (Reasonable)",
        "description": "Right to audit at any time with 90 days advance notice.",
        "keywords": ["90 day", "90-day", "ninety day", "advance notice"],
    },
    {
        "id": "30_day_data_delivery",
        "label": "30-Day Data Delivery Guarantee",
        "description": "PBM must provide complete claim files and documentation within 30 days of data request.",
        "keywords": ["30 day", "30-day", "thirty day", "data delivery", "claim files within"],
    },
    {
        "id": "30_day_finding_response",
        "label": "30-Day Audit Finding Response",
        "description": "PBM agrees to 30-day turnaround for full responses to sample claims and audit findings.",
        "keywords": ["finding response", "turnaround", "respond to", "findings within"],
    },
    {
        "id": "financial_guarantees_turnaround",
        "label": "Financial Guarantees for Turnaround Times",
        "description": "PBM agrees to financial guarantees (penalties) for turnaround times at each audit stage.",
        "keywords": ["financial guarantee", "penalty", "liquidated damage", "turnaround guarantee"],
    },
    {
        "id": "error_correction",
        "label": "Error Correction Obligation",
        "description": "PBM will correct any errors brought to attention whether identified by audit or otherwise.",
        "keywords": ["correct", "error correction", "fix", "remedy", "rectify"],
    },
    {
        "id": "manufacturer_contract_access",
        "label": "Manufacturer Contract Access (Up to 12)",
        "description": "Right to audit up to 12 pharmaceutical manufacturer contracts during on-site rebate audit.",
        "keywords": ["manufacturer contract", "rebate contract", "on-site", "manufacturer agreement", "12 manufacturer"],
    },
    {
        "id": "survival_post_termination",
        "label": "3-Year Survival Post-Termination",
        "description": "Audit right survives termination of agreement for 3 years.",
        "keywords": ["surviv", "post-termination", "after termination", "beyond termination"],
    },
    {
        "id": "no_cost_to_plan",
        "label": "No Audit Cost to Plan Sponsor",
        "description": "Plan not responsible for PBM time/costs associated with audit process, including data provision, response reports, and systems access.",
        "keywords": ["no cost", "no charge", "not responsible for", "pbm's expense", "no additional charge", "at no cost"],
    },
]


def score_audit_rights(contract_analysis: dict) -> dict:
    """Score a parsed contract's audit rights against the gold-standard template."""
    audit_section = contract_analysis.get("audit_rights", {})
    audit_text = " ".join([
        str(audit_section.get("details", "")),
        str(audit_section.get("frequency", "")),
        str(audit_section.get("scope", "")),
        str(contract_analysis.get("summary", "")),
    ]).lower()

    # Also check compliance flags for audit-related flags
    for flag in contract_analysis.get("compliance_flags", []):
        audit_text += " " + str(flag.get("issue", "")).lower()
        audit_text += " " + str(flag.get("recommendation", "")).lower()

    results = []
    found_count = 0
    for item in GOLD_STANDARD_AUDIT_RIGHTS:
        present = any(kw in audit_text for kw in item["keywords"])
        if present:
            found_count += 1
        results.append({
            "id": item["id"],
            "label": item["label"],
            "description": item["description"],
            "present": present,
            "status": "found" if present else "missing",
        })

    score = round((found_count / len(GOLD_STANDARD_AUDIT_RIGHTS)) * 100)
    missing = [r for r in results if not r["present"]]

    if score >= 80:
        grade = "A"
        assessment = "Strong audit protections. Contract includes most gold-standard provisions."
    elif score >= 60:
        grade = "B"
        assessment = "Moderate audit protections. Several important provisions are missing."
    elif score >= 40:
        grade = "C"
        assessment = "Weak audit protections. Contract favors PBM over plan sponsor."
    else:
        grade = "D"
        assessment = "Very weak audit protections. Contract severely limits audit effectiveness. High risk of PBM overcharging going undetected."

    recommendations = []
    for m in missing:
        recommendations.append(f"Add: {m['label']} — {m['description']}")

    return {
        "score": score,
        "grade": grade,
        "found": found_count,
        "total": len(GOLD_STANDARD_AUDIT_RIGHTS),
        "assessment": assessment,
        "provisions": results,
        "missing_count": len(missing),
        "recommendations": recommendations,
    }

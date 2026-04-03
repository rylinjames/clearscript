"""
Prior Authorization Value Detector Service.
Analyzes PA rules and outputs Keep/Remove/Modify recommendations.
Uses gold carding benchmarks and CMS 2026 PA rule data.
"""

import random

# Synthetic PA rules with approval rates (simulating real formulary PA data)
PA_RULES = [
    {"drug": "Humira 40mg", "drug_class": "Biologic (TNF)", "pa_type": "Clinical PA", "approval_rate": 0.92, "avg_review_days": 3.2, "annual_pa_volume": 145, "admin_cost_per_pa": 85, "clinical_rationale": "Step therapy: must try methotrexate first", "specialty": True},
    {"drug": "Ozempic 1mg", "drug_class": "GLP-1 Agonist", "pa_type": "Clinical PA", "approval_rate": 0.88, "avg_review_days": 2.8, "annual_pa_volume": 312, "admin_cost_per_pa": 85, "clinical_rationale": "Diagnosis confirmation (T2D), BMI threshold for weight", "specialty": False},
    {"drug": "Dupixent 300mg", "drug_class": "Biologic (IL-4)", "pa_type": "Clinical PA", "approval_rate": 0.78, "avg_review_days": 4.1, "annual_pa_volume": 67, "admin_cost_per_pa": 85, "clinical_rationale": "Failed topical therapy, confirmed atopic dermatitis diagnosis", "specialty": True},
    {"drug": "Eliquis 5mg", "drug_class": "Anticoagulant", "pa_type": "Quantity Limit", "approval_rate": 0.96, "avg_review_days": 1.2, "annual_pa_volume": 520, "admin_cost_per_pa": 45, "clinical_rationale": "Standard dose verification", "specialty": False},
    {"drug": "Jardiance 25mg", "drug_class": "SGLT2 Inhibitor", "pa_type": "Step Therapy", "approval_rate": 0.94, "avg_review_days": 2.0, "annual_pa_volume": 280, "admin_cost_per_pa": 65, "clinical_rationale": "Must try metformin first", "specialty": False},
    {"drug": "Keytruda 200mg", "drug_class": "Oncology", "pa_type": "Clinical PA", "approval_rate": 0.65, "avg_review_days": 5.5, "annual_pa_volume": 32, "admin_cost_per_pa": 120, "clinical_rationale": "Tumor type, PD-L1 expression, prior treatments", "specialty": True},
    {"drug": "Vyvanse 50mg", "drug_class": "ADHD", "pa_type": "Clinical PA", "approval_rate": 0.91, "avg_review_days": 2.5, "annual_pa_volume": 195, "admin_cost_per_pa": 65, "clinical_rationale": "ADHD diagnosis confirmation, age-appropriate dosing", "specialty": False},
    {"drug": "Stelara 90mg", "drug_class": "Biologic (IL-23)", "pa_type": "Clinical PA", "approval_rate": 0.74, "avg_review_days": 4.8, "annual_pa_volume": 48, "admin_cost_per_pa": 120, "clinical_rationale": "Failed conventional therapy, confirmed psoriasis/Crohn's", "specialty": True},
    {"drug": "Trulicity 1.5mg", "drug_class": "GLP-1 Agonist", "pa_type": "Step Therapy", "approval_rate": 0.95, "avg_review_days": 1.8, "annual_pa_volume": 240, "admin_cost_per_pa": 65, "clinical_rationale": "Must try metformin first", "specialty": False},
    {"drug": "Xarelto 20mg", "drug_class": "Anticoagulant", "pa_type": "Quantity Limit", "approval_rate": 0.97, "avg_review_days": 1.0, "annual_pa_volume": 410, "admin_cost_per_pa": 45, "clinical_rationale": "Standard dose verification", "specialty": False},
    {"drug": "Entresto 97/103mg", "drug_class": "Heart Failure", "pa_type": "Clinical PA", "approval_rate": 0.85, "avg_review_days": 3.0, "annual_pa_volume": 110, "admin_cost_per_pa": 85, "clinical_rationale": "Confirmed HFrEF, LVEF criteria", "specialty": False},
    {"drug": "Symbicort 160/4.5", "drug_class": "Inhaler", "pa_type": "Step Therapy", "approval_rate": 0.93, "avg_review_days": 1.5, "annual_pa_volume": 350, "admin_cost_per_pa": 55, "clinical_rationale": "Must try generic ICS first", "specialty": False},
    {"drug": "Insulin Glargine", "drug_class": "Insulin", "pa_type": "Quantity Limit", "approval_rate": 0.98, "avg_review_days": 0.8, "annual_pa_volume": 680, "admin_cost_per_pa": 35, "clinical_rationale": "Dose verification", "specialty": False},
    {"drug": "Atorvastatin 40mg", "drug_class": "Statin", "pa_type": "None", "approval_rate": 1.0, "avg_review_days": 0, "annual_pa_volume": 0, "admin_cost_per_pa": 0, "clinical_rationale": "No PA required (generic)", "specialty": False},
    {"drug": "Metformin 500mg", "drug_class": "Antidiabetic", "pa_type": "None", "approval_rate": 1.0, "avg_review_days": 0, "annual_pa_volume": 0, "admin_cost_per_pa": 0, "clinical_rationale": "No PA required (generic first-line)", "specialty": False},
]

GOLD_CARD_THRESHOLD = 0.90  # If >90% approval, PA is likely not adding clinical value
MODIFY_THRESHOLD = 0.80     # Between 80-90%, consider modifying criteria
KEEP_THRESHOLD = 0.80       # Below 80%, PA is working — keep it


def _recommend(rule: dict) -> dict:
    """Generate Keep/Remove/Modify recommendation for a PA rule."""
    if rule["pa_type"] == "None":
        return {**rule, "recommendation": "N/A", "rationale": "No PA in place", "admin_waste": 0, "gold_card_eligible": False}

    rate = rule["approval_rate"]
    volume = rule["annual_pa_volume"]
    admin_cost = rule["admin_cost_per_pa"]
    annual_waste = round(volume * admin_cost * rate, 0)  # Cost of approving PAs that would have been fine

    if rate >= GOLD_CARD_THRESHOLD:
        rec = "REMOVE"
        rationale = f"{rate:.0%} approval rate means this PA catches only {1-rate:.0%} of cases. Admin cost (${annual_waste:,.0f}/yr) far exceeds clinical value. Gold card eligible."
        gold_card = True
    elif rate >= MODIFY_THRESHOLD:
        rec = "MODIFY"
        rationale = f"{rate:.0%} approval rate — PA has some value but criteria may be too broad. Consider narrowing to high-risk subgroups or converting to retrospective review."
        gold_card = False
    else:
        rec = "KEEP"
        rationale = f"{rate:.0%} approval rate — PA is preventing {1-rate:.0%} inappropriate utilization. Clinical value justifies admin burden."
        gold_card = False

    return {
        **rule,
        "recommendation": rec,
        "rationale": rationale,
        "annual_admin_waste": annual_waste,
        "gold_card_eligible": gold_card,
    }


def analyze_prior_auth_value() -> dict:
    """Analyze all PA rules and generate Keep/Remove/Modify recommendations."""
    results = [_recommend(r) for r in PA_RULES]
    pa_rules_only = [r for r in results if r["pa_type"] != "None"]

    remove_count = sum(1 for r in pa_rules_only if r["recommendation"] == "REMOVE")
    modify_count = sum(1 for r in pa_rules_only if r["recommendation"] == "MODIFY")
    keep_count = sum(1 for r in pa_rules_only if r["recommendation"] == "KEEP")
    total_waste = sum(r.get("annual_admin_waste", 0) for r in pa_rules_only if r["recommendation"] == "REMOVE")
    gold_card_eligible = sum(1 for r in pa_rules_only if r.get("gold_card_eligible"))

    return {
        "summary": {
            "total_pa_rules_analyzed": len(pa_rules_only),
            "remove": remove_count,
            "modify": modify_count,
            "keep": keep_count,
            "gold_card_eligible_providers": gold_card_eligible,
            "total_annual_admin_waste_removable": round(total_waste),
            "avg_approval_rate": round(sum(r["approval_rate"] for r in pa_rules_only) / len(pa_rules_only), 3),
        },
        "rules": results,
        "gold_carding_context": {
            "description": "Gold carding exempts high-approval-rate providers from PA requirements",
            "states_with_laws": ["Texas", "Arkansas", "West Virginia"],
            "cms_2026_rule": "CMS requires MA/Medicaid/ACA plans to publish PA approval/denial metrics starting 2026. Urgent PA response: 72 hours. Routine: 7 days.",
            "highmark_benchmark": "25,000+ providers gold-carded, 85-90% admin time reduction",
            "texas_reality": "Only 3% of physicians achieved gold card status despite legislation",
            "musc_savings": "5,000+ staff hours/month reclaimed with PA automation",
        },
        "recommendations": [
            f"Remove {remove_count} low-value PAs to save ~${total_waste:,.0f}/year in admin costs",
            f"Modify {modify_count} PAs with borderline approval rates — narrow criteria to high-risk subgroups",
            f"Keep {keep_count} PAs that are preventing inappropriate utilization",
            f"{gold_card_eligible} drug categories are gold-card eligible (>90% approval rate)",
            "Implement gold carding for high-performing providers to reduce admin burden without losing clinical oversight",
        ],
    }

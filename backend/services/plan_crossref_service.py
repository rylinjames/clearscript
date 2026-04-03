"""
Plan Intelligence Cross-Reference Service.
Compares PBM contract analysis against plan document (SBC/SPD/EOC) benefits
to flag gaps, mismatches, and areas of concern.
"""

import json
import logging
from services.ai_service import _generate

logger = logging.getLogger(__name__)

CROSSREF_SYSTEM_PROMPT = """You are a senior benefits consultant reviewing an employer's PBM contract alongside their plan document (SBC/SPD/EOC).

Your job is to cross-reference the two documents and identify:
1. MISMATCHES — where the contract terms don't align with what the plan document says
2. GAPS — important items in one document that are missing from the other
3. RISKS — areas where the plan sponsor may be exposed based on the combination of both documents
4. RECOMMENDATIONS — specific actions the employer should take

Return valid JSON with exactly this structure:

{
  "summary": "string — 2-3 sentence executive summary of the cross-reference findings",
  "overall_alignment_score": 75,
  "findings": [
    {
      "category": "string (e.g. 'Prescription Drug Coverage', 'Cost Sharing', 'Audit Rights', 'Formulary', 'Network')",
      "finding": "string — what was found",
      "severity": "high | medium | low",
      "contract_says": "string — what the PBM contract states",
      "plan_doc_says": "string — what the plan document states",
      "recommendation": "string — what the employer should do"
    }
  ],
  "rx_alignment": {
    "contract_tier_structure_matches_plan": true,
    "copay_amounts_consistent": true,
    "mail_order_terms_consistent": true,
    "specialty_terms_consistent": true,
    "formulary_referenced_correctly": true,
    "notes": "string"
  },
  "cost_sharing_gaps": [
    "string — specific cost-sharing discrepancy or gap"
  ],
  "missing_from_contract": [
    "string — items in the plan doc that should be addressed in the PBM contract"
  ],
  "missing_from_plan_doc": [
    "string — PBM contract terms not reflected in the plan document"
  ],
  "action_items": [
    {
      "priority": "high | medium | low",
      "action": "string — specific action to take",
      "reason": "string — why this matters"
    }
  ]
}

IMPORTANT:
- Be specific and cite actual values from both documents.
- Flag any case where the plan document references terms not defined in the contract.
- Pay special attention to Rx tier structures, copay amounts, mail order requirements, specialty drug handling, and formulary references.
- overall_alignment_score is 0-100 where 100 means perfect alignment.
"""


async def cross_reference_contract_and_plan(contract_analysis: dict, plan_benefits: dict) -> dict:
    """
    Cross-reference a PBM contract analysis against parsed plan document benefits.

    Args:
        contract_analysis: Output from the contract parsing pipeline (rebate terms, audit rights, etc.)
        plan_benefits: Output from the SPC/plan document parser (deductibles, copays, Rx tiers, etc.)

    Returns:
        Dict with cross-reference findings, gaps, and recommendations.
    """
    try:
        prompt = (
            "Cross-reference this PBM contract analysis against the plan document benefits.\n\n"
            f"=== PBM CONTRACT ANALYSIS ===\n{json.dumps(contract_analysis, indent=2, default=str)[:8000]}\n\n"
            f"=== PLAN DOCUMENT BENEFITS ===\n{json.dumps(plan_benefits, indent=2, default=str)[:8000]}"
        )
        result = await _generate(CROSSREF_SYSTEM_PROMPT, prompt, 4000)
        parsed = json.loads(result)
        parsed["_generated_by"] = "ai"
        logger.info(f"Cross-reference completed via AI, alignment_score={parsed.get('overall_alignment_score', 'N/A')}")
        return parsed
    except Exception as e:
        logger.warning(f"AI cross-reference failed, using mock: {e}")
        result = _mock_cross_reference()
        result["_generated_by"] = "mock"
        return result


def _mock_cross_reference() -> dict:
    """Realistic mock cross-reference results for demo."""
    return {
        "summary": "The PBM contract and plan document show moderate alignment but have significant gaps in specialty drug handling, mail-order requirements, and rebate transparency. The plan document references a 4-tier Rx structure while the contract pricing implies different tier definitions. Several cost-sharing terms in the plan document are not backed by corresponding contract guarantees.",
        "overall_alignment_score": 62,
        "findings": [
            {
                "category": "Prescription Drug Coverage",
                "finding": "Tier structure mismatch between contract and plan document",
                "severity": "high",
                "contract_says": "Pricing based on AWP-15% brand, AWP-75% generic at retail",
                "plan_doc_says": "4-tier structure: Generic $10, Preferred Brand $35, Non-Preferred $70, Specialty 20% up to $250",
                "recommendation": "Verify that the AWP discount guarantees in the contract produce member copays consistent with the plan document tier structure. Request a reconciliation showing how contract pricing translates to member cost-sharing."
            },
            {
                "category": "Mail Order",
                "finding": "Mandatory mail-order requirement in contract not clearly stated in plan document",
                "severity": "medium",
                "contract_says": "Members required to use mail-order after second retail fill of maintenance medications",
                "plan_doc_says": "Mail-order available at 2.5x retail copay for 90-day supply. No mandatory language.",
                "recommendation": "Align plan document language with the contract's mandatory mail-order requirement, or negotiate to remove the mandate from the contract if the plan design is intended to be voluntary."
            },
            {
                "category": "Specialty Drugs",
                "finding": "Specialty drug exclusive channel not disclosed in plan document",
                "severity": "high",
                "contract_says": "All specialty medications dispensed exclusively through PBM's specialty pharmacy division. No carve-out permitted.",
                "plan_doc_says": "Specialty drugs: 20% coinsurance up to $250 per fill. No mention of exclusive pharmacy requirement.",
                "recommendation": "Plan document should disclose that specialty drugs must be obtained through the PBM's specialty pharmacy. Members may not be aware of this restriction. This could create grievance exposure."
            },
            {
                "category": "Formulary",
                "finding": "Contract allows PBM sole discretion on formulary changes; plan document references a specific formulary",
                "severity": "medium",
                "contract_says": "PBM may modify the Formulary at its sole discretion upon 60 days' notice. PBM is not required to obtain Plan Sponsor approval for tier placement changes.",
                "plan_doc_says": "Covered drugs are those listed on the Standard National Formulary.",
                "recommendation": "Negotiate for Plan Sponsor approval rights on tier changes that affect member cost-sharing. The current contract gives the PBM unilateral control over which drugs cost members more."
            },
            {
                "category": "Cost Sharing",
                "finding": "Deductible applicability not specified in contract",
                "severity": "low",
                "contract_says": "No mention of deductible interaction with Rx benefits",
                "plan_doc_says": "Rx deductible applies to Tiers 3 and 4 only",
                "recommendation": "Ensure claims adjudication system is configured to apply deductible correctly per plan document. Verify during audit that Tier 3/4 claims are applying deductible before coinsurance."
            },
            {
                "category": "Audit Rights",
                "finding": "Contract audit scope would not allow verification of all plan document benefit provisions",
                "severity": "high",
                "contract_says": "Audits limited to pricing and rebate terms. Manufacturer contracts, pharmacy network agreements, and internal cost structures excluded.",
                "plan_doc_says": "N/A — plan document does not reference audit rights",
                "recommendation": "The restricted audit scope means the Plan Sponsor cannot verify that member cost-sharing is being applied correctly, that the formulary matches what was agreed, or that the specialty pharmacy exclusive arrangement is operating as intended. Negotiate for unrestricted audit scope per new DOL requirements."
            },
        ],
        "rx_alignment": {
            "contract_tier_structure_matches_plan": False,
            "copay_amounts_consistent": False,
            "mail_order_terms_consistent": False,
            "specialty_terms_consistent": False,
            "formulary_referenced_correctly": True,
            "notes": "The contract defines pricing in AWP discount terms while the plan document defines member cost-sharing in flat copay terms. There is no contractual mechanism to ensure AWP discounts produce the copay amounts promised in the plan document."
        },
        "cost_sharing_gaps": [
            "No contract guarantee that AWP-15% brand pricing results in the $35 Tier 2 copay stated in the plan document",
            "Specialty drug $250/fill cap in plan document has no corresponding contract guarantee",
            "Deductible interaction with Rx tiers is defined in plan document but not in PBM contract",
            "Emergency prescription provisions in plan document not addressed in contract"
        ],
        "missing_from_contract": [
            "Member appeal rights for formulary exceptions",
            "Step therapy protocols and override procedures",
            "Specialty drug prior authorization turnaround time guarantees",
            "Transition fill provisions for new members"
        ],
        "missing_from_plan_doc": [
            "Mandatory mail-order requirement after second retail fill",
            "Specialty pharmacy exclusive channel restriction",
            "MAC pricing methodology (affects generic out-of-pocket costs)",
            "Spread pricing retention by PBM"
        ],
        "action_items": [
            {
                "priority": "high",
                "action": "Negotiate unrestricted audit scope in the PBM contract",
                "reason": "Current scope prevents verification of member cost-sharing accuracy, formulary compliance, and specialty pharmacy operations. DOL rules effective July 2026 require unrestricted audit rights."
            },
            {
                "priority": "high",
                "action": "Add specialty pharmacy disclosure language to the plan document",
                "reason": "Members are currently unaware that specialty drugs must be obtained through the PBM's pharmacy. This creates potential grievance and compliance exposure."
            },
            {
                "priority": "high",
                "action": "Request a copay reconciliation showing how contract AWP discounts translate to member tier copays",
                "reason": "There is no contractual link between the AWP discount guarantees and the member copay amounts in the plan document. The PBM could be compliant with AWP-15% while members pay more than the plan document states."
            },
            {
                "priority": "medium",
                "action": "Align mail-order language between contract and plan document",
                "reason": "The contract mandates mail-order for maintenance drugs but the plan document presents it as optional. This inconsistency could cause member confusion and grievances."
            },
            {
                "priority": "medium",
                "action": "Add step therapy and PA turnaround guarantees to the PBM contract",
                "reason": "The plan document implies these processes exist but the contract has no performance standards around them."
            },
            {
                "priority": "low",
                "action": "Include transition fill provisions in both documents",
                "reason": "New members switching from a previous plan may lose access to medications not on the current formulary. Standard practice is 30-day transition fills."
            }
        ]
    }

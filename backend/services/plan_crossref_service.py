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


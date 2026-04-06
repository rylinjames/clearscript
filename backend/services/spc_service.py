"""
SPC (Summary of Plan Coverage) Parser Service.
Extracts structured benefit data from SPC/SBC/SPD/EOC text via the shared
OpenAI-backed `_generate` helper in services.ai_service.

Failures (missing key, API error, bad JSON) propagate to the router, which
turns them into HTTP 503. No mock fallback — stale canned data would be
worse than a real error.
"""

import json
import logging

from services.ai_service import _generate

logger = logging.getLogger(__name__)

# ─── AI Prompts ────────────────────────────────────────────────────────────────

SPC_PARSE_SYSTEM_PROMPT = """You are a health insurance plan document analyst. Extract structured benefit data from the provided SBC, SPD, or EOC/COC document.

Focus on the fields that matter for PBM contract cross-referencing. Do NOT include AWP comparisons — AWP is what the plan pays, not what the employee pays.

Return valid JSON with exactly this structure:

{
  "plan_info": {
    "plan_name": "string or null",
    "carrier": "string or null",
    "effective_date": "string or null",
    "plan_type": "string or null (e.g. PPO, HMO, HDHP, POS)"
  },
  "deductible": {
    "individual_in_network": "string or null (e.g. '$1,500')",
    "family_in_network": "string or null",
    "notes": "string or null"
  },
  "out_of_pocket_maximum": {
    "individual_in_network": "string or null",
    "family_in_network": "string or null"
  },
  "copays": {
    "pcp_visit": "string or null",
    "specialist_visit": "string or null",
    "emergency_room": "string or null",
    "urgent_care": "string or null"
  },
  "coinsurance": {
    "in_network": "string or null (e.g. '80/20 after deductible')",
    "out_of_network": "string or null"
  },
  "prescription_drugs": {
    "tier_1_generic": "string or null (e.g. '$10 copay')",
    "tier_2_preferred_brand": "string or null",
    "tier_3_non_preferred": "string or null",
    "tier_4_specialty": "string or null",
    "deductible_applies": "string or null (which tiers require deductible)",
    "mail_order_available": "string or null",
    "pbm_name": "string or null",
    "mandatory_mail_order": "string or null"
  },
  "key_exclusions": [
    "string — only notable Rx-relevant exclusions (e.g. specialty drug restrictions, step therapy, PA requirements)"
  ],
  "confidence_score": 85
}

IMPORTANT:
- confidence_score MUST be an integer 0-100.
- Use null for any field you cannot find. Do not guess.
- Preserve exact dollar amounts as written.
- Focus on Rx-relevant benefits for PBM contract cross-referencing.
- Do NOT include hospital services, lab work, imaging, rehabilitation, or DME — these are not relevant to PBM analysis.
"""

SPC_COMPARE_SYSTEM_PROMPT = """You are a health insurance benefits analyst comparing two Summary of Plan Coverage (SPC) documents.

Analyze both plans and return a structured comparison. Return valid JSON with exactly this structure:

{
  "plan_a_name": "string",
  "plan_b_name": "string",
  "comparison": [
    {
      "category": "string (e.g. 'Deductible', 'Copays', 'Prescription Drugs')",
      "benefit": "string (specific benefit being compared)",
      "plan_a_value": "string",
      "plan_b_value": "string",
      "difference": "string (plain English description of the difference)",
      "advantage": "plan_a | plan_b | equal"
    }
  ],
  "cost_analysis": {
    "lower_premium_likely": "plan_a | plan_b | unclear",
    "lower_out_of_pocket_likely": "plan_a | plan_b | unclear",
    "better_for_healthy_individual": "plan_a | plan_b | equal",
    "better_for_high_utilizer": "plan_a | plan_b | equal",
    "better_rx_coverage": "plan_a | plan_b | equal",
    "notes": "string"
  },
  "prescription_drug_comparison": {
    "generic_advantage": "plan_a | plan_b | equal",
    "brand_advantage": "plan_a | plan_b | equal",
    "specialty_advantage": "plan_a | plan_b | equal",
    "mail_order_advantage": "plan_a | plan_b | equal",
    "notes": "string"
  },
  "key_differences": ["string — most important difference to highlight"],
  "recommendation": "string — overall assessment of which plan is better for different scenarios"
}

IMPORTANT: Be objective and thorough. Base all comparisons on the actual values extracted. If a value is missing from one plan, note it as 'Not specified'.
"""


async def parse_spc(text: str) -> dict:
    """
    Parse an SPC/SBC/SPD/EOC document into structured benefit data via OpenAI.
    Raises on any failure.
    """
    result = await _generate(
        SPC_PARSE_SYSTEM_PROMPT,
        f"Extract structured benefit data from this Summary of Plan Coverage:\n\n{text[:15000]}",
        16000,
    )
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    logger.info(f"SPC parsed successfully via AI, confidence={parsed.get('confidence_score', 'N/A')}")
    return parsed


async def compare_spcs(text_a: str, text_b: str) -> dict:
    """
    Compare two SPC/SBC documents side by side via OpenAI. Raises on failure.
    """
    prompt = (
        "Compare these two Summary of Plan Coverage documents:\n\n"
        f"=== PLAN A ===\n{text_a[:8000]}\n\n"
        f"=== PLAN B ===\n{text_b[:8000]}"
    )
    result = await _generate(SPC_COMPARE_SYSTEM_PROMPT, prompt, 16000)
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    logger.info("SPC comparison completed via AI")
    return parsed


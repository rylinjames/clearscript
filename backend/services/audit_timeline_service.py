"""
Audit Timeline Tracker Service.
Generates milestone-based audit timelines with PBM delay tactic warnings.

Based on intel from Nick Beckman (Segal) — real PBM audit timeline:
- Plan year ends (e.g. Dec 31)
- 90-day run-out period (~Apr 1) for claims to finish processing
- Data request sent to PBM
- 4-12 weeks for PBM to compile and deliver data
- 60-90 days for audit execution (~60 days NDC-level checking, ~30 days review/finalize)
- Total: audit may not complete until July-August of following year
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── PBM Delay Tactics Database ────────────────────────────────────────────────

PBM_DELAY_TACTICS = {
    "data_request": [
        {
            "tactic": "Limit concurrent audits",
            "description": "PBM contract may limit the number of audits that can run simultaneously across all clients. PBM uses this to queue your audit behind others.",
            "contract_cite": "Look for 'concurrent audit limitation' or 'audit scheduling' clauses in the Audit Rights section.",
            "countermeasure": "Negotiate removal of concurrent audit caps. If cap exists, send your audit notice as early as possible to secure your slot.",
        },
        {
            "tactic": "Demand excessive advance notice",
            "description": "PBM insists on 120-180 day advance notice before audit can begin, pushing timeline further out.",
            "contract_cite": "Check 'Advance Notice' requirements — gold standard is 90 days. Anything above 90 is a red flag.",
            "countermeasure": "Send notice immediately after run-out period ends. Do not wait for final data to send notice.",
        },
        {
            "tactic": "Restrict auditor to PBM-approved list",
            "description": "PBM requires you to select auditor from their pre-approved list, limiting independence.",
            "contract_cite": "Check for 'auditor selection' or 'approved auditor' language in Audit Rights section.",
            "countermeasure": "Negotiate 'auditor of choice' language. If stuck with approved list, verify auditors have no financial relationship with PBM.",
        },
    ],
    "data_delivery": [
        {
            "tactic": "Provide only a sample of claims",
            "description": "PBM provides a random sample (e.g. 500 claims) instead of the full claims universe, drastically limiting audit scope.",
            "contract_cite": "Look for 'sample' or 'representative subset' language. Contract should specify 'complete claims file' or 'full universe of claims.'",
            "countermeasure": "Demand complete electronic claims file at NDC level. Cite ERISA fiduciary duty to review all plan expenditures.",
        },
        {
            "tactic": "Deliver data in unusable format",
            "description": "PBM sends paper printouts, password-protected files with delayed credentials, or data missing key fields (e.g., no pharmacy reimbursement amounts).",
            "contract_cite": "Contract should specify 'electronic format' and list required data fields explicitly.",
            "countermeasure": "Specify required format (CSV/Excel with named columns) and required fields in the data request letter. Set a cure period for incomplete data.",
        },
        {
            "tactic": "Legal review delays",
            "description": "PBM legal team adds weeks of review before releasing data, citing confidentiality or proprietary concerns.",
            "contract_cite": "Check if contract has data delivery deadlines with financial penalties for late delivery.",
            "countermeasure": "Include financial guarantee language for data delivery turnaround (e.g., $1,000/day penalty for late delivery).",
        },
        {
            "tactic": "Internal ticketing bottleneck",
            "description": "PBM routes your request through an internal ticketing system with no SLA, adding 2-4 weeks of dead time.",
            "contract_cite": "Look for 'data delivery timeline' or 'response deadline' clauses. Gold standard is 30 days.",
            "countermeasure": "Establish a named PBM contact for audit requests. Escalate to PBM account executive if ticket is not acknowledged within 5 business days.",
        },
    ],
    "audit_execution": [
        {
            "tactic": "Insist on no statistical extrapolation",
            "description": "PBM contract says errors found in audit sample cannot be extrapolated — PBM pays back only the exact errors found in reviewed claims.",
            "contract_cite": "Look for 'extrapolation' or 'statistical sampling' language. If prohibited, audit recoveries will be a fraction of actual overcharges.",
            "countermeasure": "Negotiate extrapolation rights before signing contract. If not possible, insist on auditing 100% of claims electronically at NDC level.",
        },
        {
            "tactic": "Dispute findings with counter-interpretations",
            "description": "PBM challenges every finding with alternative contract interpretations, dragging out the resolution phase.",
            "contract_cite": "Check dispute resolution timeline — should have a defined period (e.g., 30 days) for PBM to accept or formally dispute findings.",
            "countermeasure": "Document each finding with specific contract section, pricing benchmark, and dollar amount. Use NDC-level MediSpan AWP data as objective pricing source.",
        },
        {
            "tactic": "Force mediation/arbitration over litigation",
            "description": "PBM contract requires binding arbitration, preventing you from going to court where discovery rules are stronger.",
            "contract_cite": "Check 'Dispute Resolution' section for mandatory arbitration or mediation clauses.",
            "countermeasure": "Negotiate to remove mandatory arbitration. At minimum, ensure arbitration rules allow document discovery and expert testimony.",
        },
    ],
    "recovery": [
        {
            "tactic": "Cap audit recoveries",
            "description": "PBM contract limits total recovery amount (e.g., capped at annual admin fee or percentage of total spend).",
            "contract_cite": "Look for 'recovery cap', 'liability limitation', or 'maximum recovery' language.",
            "countermeasure": "Remove recovery caps entirely. If PBM overcharged, full restitution should be the standard.",
        },
        {
            "tactic": "Offset recoveries against performance guarantees",
            "description": "PBM credits audit recoveries against existing performance guarantee payments, resulting in no net new recovery.",
            "contract_cite": "Check if audit recoveries are treated as separate from performance guarantee true-ups.",
            "countermeasure": "Ensure contract explicitly states audit recoveries are in addition to any performance guarantee payments.",
        },
    ],
}

# ─── Default Contract Terms ────────────────────────────────────────────────────

DEFAULT_CONTRACT_TERMS = {
    "notice_requirement_days": 90,
    "data_delivery_deadline_days": 30,
    "response_deadline_days": 30,
    "audit_frequency": "annual",
    "run_out_period_days": 90,
    "auditor_selection": "plan_choice",
    "extrapolation_allowed": False,
    "concurrent_audit_limit": None,
    "recovery_cap": None,
    "dispute_resolution": "arbitration",
    "survival_years": 3,
}


def generate_audit_timeline(plan_year_end: str, contract_terms: dict) -> dict:
    """
    Generate a milestone-based audit timeline with PBM delay tactic warnings.

    Args:
        plan_year_end: Plan year end date in YYYY-MM-DD format (e.g. "2025-12-31")
        contract_terms: Dict of contract terms overriding defaults. Keys:
            - notice_requirement_days (int): Days of advance notice required
            - data_delivery_deadline_days (int): Days PBM has to deliver data
            - response_deadline_days (int): Days PBM has to respond to findings
            - audit_frequency (str): "annual", "biennial", etc.
            - run_out_period_days (int): Days after plan year end for claims run-out
            - auditor_selection (str): "plan_choice" or "pbm_approved"
            - extrapolation_allowed (bool): Whether statistical extrapolation is permitted
            - concurrent_audit_limit (int or None): Max concurrent audits
            - recovery_cap (str or None): Cap on audit recoveries
            - dispute_resolution (str): "arbitration", "mediation", "litigation"

    Returns:
        Dict with milestones, total_duration_days, risk_factors, recommended_actions
    """
    # Merge with defaults
    terms = {**DEFAULT_CONTRACT_TERMS, **contract_terms}

    try:
        pye_date = datetime.strptime(plan_year_end, "%Y-%m-%d")
    except (ValueError, TypeError):
        logger.warning(f"Invalid plan_year_end '{plan_year_end}', defaulting to Dec 31 of current year")
        now = datetime.now()
        pye_date = datetime(now.year, 12, 31)

    run_out_days = terms.get("run_out_period_days", 90)
    notice_days = terms.get("notice_requirement_days", 90)
    data_delivery_days = terms.get("data_delivery_deadline_days", 30)
    response_days = terms.get("response_deadline_days", 30)

    # ─── Build milestone timeline ──────────────────────────────────────────────

    milestones = []
    current_date = pye_date

    # Milestone 1: Plan year end
    milestones.append({
        "id": "plan_year_end",
        "label": "Plan Year End",
        "date": current_date.strftime("%Y-%m-%d"),
        "description": f"Plan year ends. Claims incurred up to this date are in scope for the audit.",
        "days_from_start": 0,
        "delay_tactics": [],
        "contract_cite": "Plan document — plan year definition.",
        "action_items": [
            "Begin preparing audit notice letter immediately.",
            "Confirm auditor engagement or begin selection process.",
            "Review contract audit rights section to confirm requirements.",
        ],
    })

    # Milestone 2: Send audit notice (can overlap with run-out)
    notice_send_date = pye_date + timedelta(days=30)
    milestones.append({
        "id": "audit_notice_sent",
        "label": "Send Audit Notice to PBM",
        "date": notice_send_date.strftime("%Y-%m-%d"),
        "description": f"Send formal written audit notice to PBM. Contract requires {notice_days} days advance notice. Sending early ensures your audit slot is secured.",
        "days_from_start": (notice_send_date - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["data_request"],
        "contract_cite": f"Audit Rights section — {notice_days}-day advance notice requirement.",
        "action_items": [
            "Send notice via certified mail AND email for documentation.",
            "Specify audit scope: claims, rebates, pricing, network.",
            "Name your selected auditor (or request PBM's approved list if required).",
            f"Set expected audit start date: {(notice_send_date + timedelta(days=notice_days)).strftime('%Y-%m-%d')}.",
        ],
    })

    # Milestone 3: Run-out period ends
    runout_end = pye_date + timedelta(days=run_out_days)
    milestones.append({
        "id": "runout_complete",
        "label": "Claims Run-Out Period Complete",
        "date": runout_end.strftime("%Y-%m-%d"),
        "description": f"{run_out_days}-day run-out period ends. All claims from the plan year should now be fully adjudicated. This is the earliest date to request final data.",
        "days_from_start": (runout_end - pye_date).days,
        "delay_tactics": [],
        "contract_cite": "Claims processing section — run-out period definition.",
        "action_items": [
            "Send formal data request letter to PBM.",
            "Specify exact data fields needed (claims, rebates, pricing, pharmacy reimbursement).",
            "Request data in electronic format (CSV/Excel) with NDC-level detail.",
            f"Set data delivery deadline: {(runout_end + timedelta(days=data_delivery_days)).strftime('%Y-%m-%d')}.",
        ],
    })

    # Milestone 4: Data request sent
    data_request_date = runout_end + timedelta(days=7)
    milestones.append({
        "id": "data_request_sent",
        "label": "Formal Data Request Sent",
        "date": data_request_date.strftime("%Y-%m-%d"),
        "description": "Formal data request sent to PBM with specific field requirements and deadline.",
        "days_from_start": (data_request_date - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["data_delivery"],
        "contract_cite": f"Audit Rights section — PBM must deliver data within {data_delivery_days} days of request.",
        "action_items": [
            "Log the request date for deadline tracking.",
            "Request read receipt or acknowledgment from PBM.",
            "Set internal reminder for follow-up at day 15 if no acknowledgment.",
        ],
    })

    # Milestone 5: Data delivery deadline (contractual)
    data_deadline = data_request_date + timedelta(days=data_delivery_days)
    milestones.append({
        "id": "data_delivery_deadline",
        "label": "PBM Data Delivery Deadline",
        "date": data_deadline.strftime("%Y-%m-%d"),
        "description": f"Contractual deadline for PBM to deliver complete audit data ({data_delivery_days} days from request).",
        "days_from_start": (data_deadline - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["data_delivery"],
        "contract_cite": f"Audit Rights section — {data_delivery_days}-day data delivery requirement.",
        "action_items": [
            "Verify data completeness against request checklist.",
            "If data is incomplete, send formal cure notice with 10-day deadline.",
            "Document any delays — they may trigger financial guarantee penalties.",
            "If no data received, escalate to PBM account executive and legal counsel.",
        ],
    })

    # Milestone 6: Realistic data receipt (PBM typically takes 4-12 weeks)
    realistic_data_receipt = data_request_date + timedelta(weeks=8)
    milestones.append({
        "id": "realistic_data_receipt",
        "label": "Realistic Data Receipt (PBM Typical)",
        "date": realistic_data_receipt.strftime("%Y-%m-%d"),
        "description": "Per industry experience, PBMs typically take 4-12 weeks to compile and deliver audit data (internal ticketing, legal review, data extraction). Plan for 8 weeks as the realistic midpoint.",
        "days_from_start": (realistic_data_receipt - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["data_delivery"],
        "contract_cite": "Track against contractual deadline. Document every day of delay beyond the contractual period.",
        "action_items": [
            "Send weekly status requests if past contractual deadline.",
            "Document all PBM communications for potential breach claim.",
            "Begin auditor prep work with any partial data received.",
        ],
    })

    # Milestone 7: Audit execution begins
    audit_start = realistic_data_receipt + timedelta(days=7)
    milestones.append({
        "id": "audit_execution_start",
        "label": "Audit Execution Begins",
        "date": audit_start.strftime("%Y-%m-%d"),
        "description": "Auditor begins NDC-level electronic claims analysis. Typical audit execution is 60-90 days: ~60 days for claims checking, ~30 days for review and finalization.",
        "days_from_start": (audit_start - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["audit_execution"],
        "contract_cite": "Audit Rights section — scope of audit, access provisions, and cooperation requirements.",
        "action_items": [
            "Ensure auditor has complete data set before starting.",
            "Establish weekly status calls with auditor.",
            "Prepare for PBM to challenge preliminary findings.",
        ],
    })

    # Milestone 8: Preliminary findings
    prelim_findings = audit_start + timedelta(days=60)
    milestones.append({
        "id": "preliminary_findings",
        "label": "Preliminary Audit Findings",
        "date": prelim_findings.strftime("%Y-%m-%d"),
        "description": "Auditor delivers preliminary findings after ~60 days of NDC-level claims review. PBM will have opportunity to respond.",
        "days_from_start": (prelim_findings - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["audit_execution"],
        "contract_cite": f"Audit Rights section — PBM has {response_days} days to respond to findings.",
        "action_items": [
            "Review preliminary findings with legal counsel.",
            "Send findings to PBM with formal response deadline.",
            f"PBM response due by: {(prelim_findings + timedelta(days=response_days)).strftime('%Y-%m-%d')}.",
            "Begin calculating potential recovery amounts.",
        ],
    })

    # Milestone 9: PBM response deadline
    pbm_response_deadline = prelim_findings + timedelta(days=response_days)
    milestones.append({
        "id": "pbm_response_deadline",
        "label": "PBM Response to Findings Deadline",
        "date": pbm_response_deadline.strftime("%Y-%m-%d"),
        "description": f"Deadline for PBM to respond to preliminary audit findings ({response_days} days).",
        "days_from_start": (pbm_response_deadline - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["recovery"],
        "contract_cite": f"Audit Rights section — {response_days}-day response requirement.",
        "action_items": [
            "Evaluate PBM response against findings.",
            "Identify accepted vs. disputed findings.",
            "For disputed items, prepare rebuttal with supporting evidence.",
        ],
    })

    # Milestone 10: Final audit report
    final_report = pbm_response_deadline + timedelta(days=30)
    milestones.append({
        "id": "final_audit_report",
        "label": "Final Audit Report",
        "date": final_report.strftime("%Y-%m-%d"),
        "description": "Final audit report incorporating PBM responses. Includes final recovery demand and recommended contract amendments.",
        "days_from_start": (final_report - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["recovery"],
        "contract_cite": "Audit Rights section — error correction and recovery provisions.",
        "action_items": [
            "Issue formal recovery demand to PBM.",
            "Set 30-day payment deadline for accepted findings.",
            "For disputed items, initiate dispute resolution process.",
            "Document lessons learned for next audit cycle.",
            "Begin negotiating contract amendments based on findings.",
        ],
    })

    # Milestone 11: Recovery deadline
    recovery_deadline = final_report + timedelta(days=30)
    milestones.append({
        "id": "recovery_deadline",
        "label": "Recovery Payment Deadline",
        "date": recovery_deadline.strftime("%Y-%m-%d"),
        "description": "Deadline for PBM to remit recovery payment for accepted audit findings.",
        "days_from_start": (recovery_deadline - pye_date).days,
        "delay_tactics": PBM_DELAY_TACTICS["recovery"],
        "contract_cite": "Audit Rights section — error correction obligation and payment timeline.",
        "action_items": [
            "Verify recovery payment received and amount matches demand.",
            "If not received, send formal breach notice.",
            "Consider next steps: dispute resolution, contract termination, or legal action.",
        ],
    })

    total_duration = (recovery_deadline - pye_date).days

    # ─── Risk factors based on contract terms ──────────────────────────────────

    risk_factors = []

    if terms.get("auditor_selection") == "pbm_approved":
        risk_factors.append({
            "factor": "PBM-Approved Auditor Requirement",
            "severity": "high",
            "description": "Contract limits auditor selection to PBM-approved list. Auditor independence may be compromised.",
            "recommendation": "Verify selected auditor has no financial relationship with PBM. Negotiate 'auditor of choice' language at next renewal.",
        })

    if not terms.get("extrapolation_allowed", False):
        risk_factors.append({
            "factor": "No Statistical Extrapolation",
            "severity": "high",
            "description": "Contract prohibits extrapolating errors found in sample to full claims universe. Audit recoveries will be limited to exact errors found in reviewed claims only.",
            "recommendation": "Insist on 100% electronic NDC-level audit to compensate. Negotiate extrapolation rights at next renewal.",
        })

    if terms.get("concurrent_audit_limit") is not None:
        risk_factors.append({
            "factor": f"Concurrent Audit Limit: {terms['concurrent_audit_limit']}",
            "severity": "medium",
            "description": f"PBM limits concurrent audits to {terms['concurrent_audit_limit']}. Your audit may be queued behind other clients.",
            "recommendation": "Send audit notice as early as possible to secure your slot. Document any scheduling delays.",
        })

    if terms.get("recovery_cap") is not None:
        risk_factors.append({
            "factor": f"Recovery Cap: {terms['recovery_cap']}",
            "severity": "high",
            "description": f"Audit recoveries are capped at {terms['recovery_cap']}. Actual overcharges may exceed this cap.",
            "recommendation": "Negotiate removal of recovery cap at next renewal. Document full overcharge amount even if recovery is capped.",
        })

    if terms.get("dispute_resolution") == "arbitration":
        risk_factors.append({
            "factor": "Mandatory Arbitration",
            "severity": "medium",
            "description": "Contract requires binding arbitration for disputes. Discovery rights are more limited than in litigation.",
            "recommendation": "Ensure arbitration rules allow document discovery and expert testimony. Negotiate removal of mandatory arbitration at next renewal.",
        })

    if terms.get("notice_requirement_days", 90) > 90:
        risk_factors.append({
            "factor": f"Extended Notice Period: {terms['notice_requirement_days']} days",
            "severity": "medium",
            "description": f"Contract requires {terms['notice_requirement_days']} days advance notice (gold standard is 90 days). This delays the audit start.",
            "recommendation": "Send notice immediately after plan year end. Negotiate 90-day notice at next renewal.",
        })

    if terms.get("data_delivery_deadline_days", 30) > 30:
        risk_factors.append({
            "factor": f"Extended Data Delivery: {terms['data_delivery_deadline_days']} days",
            "severity": "medium",
            "description": f"PBM has {terms['data_delivery_deadline_days']} days to deliver data (gold standard is 30 days). Expect further delays beyond this deadline.",
            "recommendation": "Negotiate 30-day data delivery with financial penalties for late delivery.",
        })

    # ─── Recommended actions ───────────────────────────────────────────────────

    recommended_actions = [
        {
            "timing": "Immediately (before plan year end)",
            "actions": [
                "Review contract audit rights section in detail.",
                "Engage or shortlist independent auditor with PBM audit experience.",
                "Prepare audit notice letter citing specific contract provisions.",
                "Budget for audit costs ($50,000-$150,000 for comprehensive NDC-level audit).",
            ],
        },
        {
            "timing": "Within 30 days of plan year end",
            "actions": [
                "Send formal audit notice to PBM via certified mail.",
                "Request PBM's approved auditor list (if required by contract).",
                "Set up internal tracking for all audit milestones and deadlines.",
            ],
        },
        {
            "timing": "During run-out period (days 1-90)",
            "actions": [
                "Prepare detailed data request specifying all required fields and formats.",
                "Brief auditor on contract terms, known concerns, and PBM history.",
                "Review prior audit findings (if any) to focus current audit scope.",
            ],
        },
        {
            "timing": "Data delivery phase",
            "actions": [
                "Track data delivery against contractual deadline.",
                "Verify data completeness against request checklist on day of receipt.",
                "Send cure notice immediately if data is incomplete or in wrong format.",
                "Document all delays for potential breach claim.",
            ],
        },
        {
            "timing": "Audit execution phase",
            "actions": [
                "Hold weekly status calls with auditor.",
                "Prepare for PBM pushback on preliminary findings.",
                "Engage legal counsel to review findings before sending to PBM.",
                "Calculate recovery demand with supporting documentation.",
            ],
        },
        {
            "timing": "Post-audit",
            "actions": [
                "Issue formal recovery demand with payment deadline.",
                "Negotiate contract amendments based on audit findings.",
                "Document lessons learned for next audit cycle.",
                "Evaluate whether to change PBMs at next renewal based on findings.",
            ],
        },
    ]

    logger.info(
        f"Generated audit timeline: plan_year_end={plan_year_end}, "
        f"total_duration={total_duration} days, risk_factors={len(risk_factors)}"
    )

    return {
        "plan_year_end": plan_year_end,
        "contract_terms": terms,
        "milestones": milestones,
        "total_duration_days": total_duration,
        "estimated_completion": recovery_deadline.strftime("%Y-%m-%d"),
        "risk_factors": risk_factors,
        "recommended_actions": recommended_actions,
        "summary": (
            f"Audit timeline spans {total_duration} days ({total_duration // 30} months) from plan year end "
            f"to expected recovery. Estimated completion: {recovery_deadline.strftime('%B %Y')}. "
            f"{len(risk_factors)} contract risk factor(s) identified that may impact audit effectiveness. "
            f"Key risk: PBM data delivery is the most common source of delays — realistic timeline is "
            f"4-12 weeks vs. contractual {data_delivery_days}-day deadline."
        ),
    }


def get_default_timeline() -> dict:
    """Generate a default timeline for a standard Jan-Dec plan year using current year."""
    current_year = datetime.now().year
    # Use most recent completed plan year
    plan_year_end = f"{current_year - 1}-12-31"
    return generate_audit_timeline(plan_year_end, DEFAULT_CONTRACT_TERMS)

"""Feature 6: Audit Request Generator"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from services.ai_service import generate_audit_letter
from services.data_service import get_claims, get_claims_status, audit_report
from services.db_service import load_latest_contract_analysis, load_contract_analysis_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])

AUDIT_TYPE_INFO = {
    "financial": {
        "description": "Verifies numbers align — claims, rebates, and spreads match contract terms.",
        "checks": [
            "AWP discount guarantees vs actual",
            "Rebate passthrough amounts",
            "Spread pricing accuracy",
            "MAC list compliance",
            "Dispensing fee accuracy",
        ],
    },
    "process": {
        "description": "Evaluates PBM administration — did they administer the plan correctly?",
        "checks": [
            "Formulary compliance",
            "Prior authorization turnaround times",
            "Claims processing accuracy",
            "Member grievance handling",
            "Network adequacy maintenance",
            "Clinical program execution",
        ],
    },
}


class AuditRequest(BaseModel):
    employer_name: Optional[str] = "Acme Corporation"
    pbm_name: Optional[str] = "OptumRx"
    contract_date: Optional[str] = None
    concerns: Optional[str] = None
    audit_type: Optional[Literal["financial", "process"]] = "financial"
    # If the user picked a specific contract from the audit-letter contract
    # picker, this is the SQLite primary key from /api/contracts/list. The
    # router loads that exact contract analysis instead of the most recent.
    contract_id: Optional[int] = None
    contract_findings: Optional[Dict[str, Any]] = None
    custom_findings: Optional[Dict[str, Any]] = None


@router.post("/generate")
async def generate_audit(request: AuditRequest = None):
    """
    Generate a formal audit request letter.
    Cites DOL rule provisions, specifies data the employer is entitled to,
    includes 10-business-day response deadline.

    audit_type controls the focus:
    - "financial": Verifies numbers (AWP discounts, rebates, spreads, MAC, dispensing fees)
    - "process": Evaluates administration (formulary, prior auth, claims accuracy, grievances, network, clinical programs)
    """
    audit_type = request.audit_type if request and request.audit_type else "financial"

    # Build contract_data from REAL sources only — no hardcoded fictional
    # findings. Order of preference:
    #   1. contract_findings explicitly passed in the request body
    #   2. The latest contract analysis persisted to SQLite (the same one
    #      the dashboard reads from), which represents the contract the
    #      user actually uploaded on the Plan Intelligence page
    #   3. Nothing — let the AI write a generic letter
    contract_data: Dict[str, Any] = {
        "employer_name": request.employer_name if request and request.employer_name else None,
        "pbm_name": request.pbm_name if request and request.pbm_name else None,
        "contract_date": request.contract_date if request and request.contract_date else None,
        "concerns": request.concerns if request and request.concerns else "",
        "audit_type": audit_type,
    }

    if request and request.contract_findings:
        contract_data["analyzed_contract"] = request.contract_findings
    elif request and request.contract_id is not None:
        # User picked a specific contract from the picker — load that one.
        try:
            picked = load_contract_analysis_by_id(request.contract_id)
            if picked and isinstance(picked.get("analysis"), dict):
                contract_data["analyzed_contract"] = picked["analysis"]
                contract_data["analyzed_contract_filename"] = picked.get("filename")
                contract_data["analyzed_contract_date"] = picked.get("analysis_date")
                contract_data["analyzed_contract_id"] = picked.get("id")
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No contract analysis found with id={request.contract_id}",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Could not load contract id={request.contract_id}: {e}")
    else:
        # Fall back to the most recent uploaded contract.
        try:
            latest = load_latest_contract_analysis()
            if latest and isinstance(latest.get("analysis"), dict):
                contract_data["analyzed_contract"] = latest["analysis"]
                contract_data["analyzed_contract_filename"] = latest.get("filename")
                contract_data["analyzed_contract_date"] = latest.get("analysis_date")
                contract_data["analyzed_contract_id"] = latest.get("id")
        except Exception as e:
            logger.warning(f"Could not load latest contract analysis for audit letter: {e}")

    has_real_contract = "analyzed_contract" in contract_data

    # Findings: only use real uploaded claims data. NEVER fall back to the
    # synthetic 500-row sample dataset — feeding made-up reconciliation
    # numbers to the AI was the root cause of the "data that doesn't make
    # sense in benchmarks and reconciliation" complaint.
    findings: Optional[Dict[str, Any]] = None
    if request and request.custom_findings:
        findings = request.custom_findings
        has_real_claims = True
    else:
        try:
            claims_status = get_claims_status()
            has_real_claims = bool(claims_status.get("custom_data_loaded"))
        except Exception:
            has_real_claims = False
        if has_real_claims:
            findings = audit_report(get_claims())
        else:
            findings = None

    # Tell the AI explicitly what is and isn't grounded in real data.
    contract_data["_data_provenance"] = {
        "has_analyzed_contract": has_real_contract,
        "has_real_claims_data": bool(findings),
        "instruction": (
            "Write the letter using ONLY the analyzed_contract data and findings "
            "above. Do not invent specific numbers, dollar amounts, percentages, "
            "spread figures, rebate amounts, or reconciliation figures that are "
            "not present in the inputs. If a category has no data, request that "
            "data generically rather than asserting any pre-existing finding."
        ),
    }

    try:
        result = await generate_audit_letter(contract_data, findings)
    except Exception as e:
        logger.error(f"Audit letter generation failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI audit letter generation is currently unavailable: {e}",
        )
    audit_type_info = AUDIT_TYPE_INFO[audit_type]

    return {
        "status": "success",
        "audit_type": audit_type,
        "audit_type_info": {
            "audit_type": audit_type,
            "description": audit_type_info["description"],
            "checklist": audit_type_info["checks"],
            "checks": audit_type_info["checks"],
        },
        "letter": result.get("letter_text", "") if isinstance(result, dict) else str(result),
        "letter_payload": result,
    }

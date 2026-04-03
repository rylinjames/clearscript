"""Feature 6: Audit Request Generator"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from services.ai_service import generate_audit_letter
from services.data_service import get_claims, audit_report

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

    contract_data = {
        "employer_name": request.employer_name if request else "Acme Corporation",
        "pbm_name": request.pbm_name if request else "OptumRx",
        "contract_date": request.contract_date if request else "January 15, 2024",
        "concerns": request.concerns if request else "",
        "audit_type": audit_type,
        "rebate_passthrough": {"found": True, "percentage": "85% of eligible rebates", "details": "Narrow definition excludes admin fees and volume bonuses"},
        "spread_pricing": {"found": True, "caps": "None", "details": "PBM retains full spread with no transparency"},
        "audit_rights": {"found": True, "scope": "Claims data only", "details": "Does not include rebate contracts or pharmacy reimbursement"},
    }

    if request and request.contract_findings:
        contract_data.update(request.contract_findings)

    if request and request.custom_findings:
        findings = request.custom_findings
    else:
        claims = get_claims()
        findings = audit_report(claims)

    result = await generate_audit_letter(contract_data, findings)

    return {
        "status": "success",
        "audit_type": audit_type,
        "audit_type_info": AUDIT_TYPE_INFO[audit_type],
        "letter": result,
    }

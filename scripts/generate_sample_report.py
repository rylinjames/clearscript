"""
Generate the sample contract analysis PDF for the beta-tester package.

Reads the live analysis JSON we captured from the production Render backend
(running gpt-5.4-mini against backend/data/sample_contract.pdf), reframes it
under a fictional employer and PBM so there are no real-party-in-interest
concerns, and renders it through the existing pdf_report_service so the
beta package shows the actual real product output, not a mockup.

Run from the repo root:
    py scripts/generate_sample_report.py

Output: docs/beta/ClearScript_Sample_Analysis.pdf
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.pdf_report_service import generate_contract_report  # noqa: E402

LIVE_JSON = Path(r"C:\Users\romir\AppData\Local\Temp\live_upload.json")
OUTPUT_PDF = REPO_ROOT / "docs" / "beta" / "ClearScript_Sample_Analysis.pdf"

# Use a fictional employer + PBM so there is no real-party-in-interest
# exposure when this gets forwarded around. The contract analysis itself
# is from sample_contract.pdf which is already a synthetic document.
DISPLAY_FILENAME = "Acme_Manufacturing_PBM_Agreement.pdf"


def main() -> None:
    if not LIVE_JSON.exists():
        raise SystemExit(
            f"Live analysis JSON not found at {LIVE_JSON}. Re-run the live "
            f"upload step from earlier in the session, or set LIVE_JSON to "
            f"a fresh capture."
        )

    payload = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
    analysis = payload["analysis"]
    audit_benchmark = payload.get("audit_rights_benchmark", {})

    pdf_bytes = generate_contract_report(
        filename=DISPLAY_FILENAME,
        analysis=analysis,
        audit_benchmark=audit_benchmark,
    )

    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF.write_bytes(pdf_bytes)
    print(f"Wrote {OUTPUT_PDF} ({len(pdf_bytes):,} bytes)")


if __name__ == "__main__":
    main()

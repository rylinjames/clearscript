"""
PDF Report Generator for ClearScript Contract Reader.
Produces a professional, branded PDF report from contract analysis results.
"""

import io
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)

# ─── Brand Colors ──────────────────────────────────────────────────────────

NAVY = colors.HexColor("#1e3a5f")
NAVY_LIGHT = colors.HexColor("#2a5f8f")
EMERALD = colors.HexColor("#10b981")
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GRAY_50 = colors.HexColor("#fafafa")
GRAY_100 = colors.HexColor("#f4f4f5")
GRAY_200 = colors.HexColor("#e4e4e7")
GRAY_500 = colors.HexColor("#71717a")
GRAY_700 = colors.HexColor("#3f3f46")
GRAY_900 = colors.HexColor("#18181b")


def _build_styles():
    """Build custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "BrandTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=NAVY,
        spaceAfter=4,
        leading=26,
    ))
    styles.add(ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=GRAY_500,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=NAVY,
        spaceBefore=20,
        spaceAfter=8,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        "SubHeader",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=GRAY_700,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=GRAY_700,
        leading=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SmallText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=GRAY_500,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        "ScoreText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=36,
        textColor=NAVY,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "StatusGood",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.HexColor("#059669"),
    ))
    styles.add(ParagraphStyle(
        "StatusBad",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=RED,
    ))
    styles.add(ParagraphStyle(
        "StatusWarn",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=AMBER,
    ))
    styles.add(ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        textColor=GRAY_500,
        alignment=TA_CENTER,
    ))
    return styles


def _status_style(status: str, styles) -> str:
    """Map status to style name."""
    if status in ("good", "employer_favorable", "found"):
        return "StatusGood"
    if status in ("critical", "pbm_favorable", "missing", "high"):
        return "StatusBad"
    return "StatusWarn"


def _status_label(status: str) -> str:
    s = status.lower()
    if s in ("good", "employer_favorable", "found"):
        return "EMPLOYER"
    if s in ("critical", "pbm_favorable", "missing"):
        return "PBM"
    return "NEUTRAL"


def _severity_color(severity: str) -> colors.Color:
    s = severity.lower()
    if s == "high":
        return colors.HexColor("#fee2e2")
    if s == "medium":
        return colors.HexColor("#fef3c7")
    return colors.HexColor("#eff6ff")


def _safe_list(value):
    return value if isinstance(value, list) else []


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def generate_contract_report(
    filename: str,
    analysis: dict,
    audit_benchmark: dict = None,
    plan_benefits: dict = None,
    cross_reference: dict = None,
    compliance_deadlines: list = None,
    audit_letter: str = None,
) -> bytes:
    """
    Generate a branded PDF report from contract analysis results.

    Returns: PDF file as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _build_styles()
    story = []

    # ─── Header / Title Page ─────────────────────────────────────────────

    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("ClearScript", styles["BrandTitle"]))
    story.append(Paragraph("PBM Contract Analysis Report", styles["BrandSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=16))

    # Report metadata
    meta_data = [
        ["Document:", filename or "PBM Contract"],
        ["Generated:", datetime.now().strftime("%B %d, %Y at %I:%M %p")],
        ["Engine:", "ClearScript AI (GPT-5.4 mini)"],
    ]
    meta_table = Table(meta_data, colWidths=[1.2 * inch, 5 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_500),
        ("TEXTCOLOR", (1, 0), (1, -1), GRAY_700),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * inch))

    # ─── 1. Executive Summary ────────────────────────────────────────────

    risk_score = analysis.get("overall_risk_score", 0) if isinstance(analysis, dict) else 0
    compliance_flags = analysis.get("compliance_flags", []) if isinstance(analysis, dict) else []
    high_flags = [f for f in compliance_flags if isinstance(f, dict) and f.get("severity") == "high"]
    medium_flags = [f for f in compliance_flags if isinstance(f, dict) and f.get("severity") == "medium"]
    weighted_assessment = _safe_dict(analysis.get("weighted_assessment")) if isinstance(analysis, dict) else {}
    financial_exposure = _safe_dict(analysis.get("financial_exposure")) if isinstance(analysis, dict) else {}
    control_map = _safe_list(analysis.get("control_map")) if isinstance(analysis, dict) else []
    control_posture = _safe_dict(analysis.get("control_posture")) if isinstance(analysis, dict) else {}
    structural_override = _safe_dict(analysis.get("structural_risk_override")) if isinstance(analysis, dict) else {}
    benchmark_observations = _safe_list(analysis.get("benchmark_observations")) if isinstance(analysis, dict) else []
    top_risks = _safe_list(analysis.get("top_risks")) if isinstance(analysis, dict) else []
    immediate_actions = _safe_list(analysis.get("immediate_actions")) if isinstance(analysis, dict) else []
    deal_diagnosis = analysis.get("deal_diagnosis", "") if isinstance(analysis, dict) else ""
    audit_implication = analysis.get("audit_implication", "") if isinstance(analysis, dict) else ""

    story.append(Paragraph("1. Executive Summary", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

    if deal_diagnosis:
        story.append(Paragraph("<b>Deal Diagnosis</b>", styles["SubHeader"]))
        story.append(Paragraph(str(deal_diagnosis), styles["Body"]))
        story.append(Spacer(1, 8))

    # Risk score box
    score_color = EMERALD if risk_score < 40 else (AMBER if risk_score < 70 else RED)
    risk_label = "LOW RISK" if risk_score < 40 else ("MODERATE RISK" if risk_score < 70 else "HIGH RISK")
    deal_score = weighted_assessment.get("deal_score", max(0, 100 - risk_score))
    weighted_risk = weighted_assessment.get("weighted_risk_score", risk_score)
    methodology = weighted_assessment.get("methodology", "")
    override_text = ""
    if structural_override.get("triggered"):
        drivers = ", ".join([str(driver) for driver in structural_override.get("drivers", [])[:4]])
        override_text = (
            f"<br/><br/><b>{structural_override.get('headline', 'Structural risk override triggered')}</b>: "
            f"{structural_override.get('rationale', '')}"
            + (f" Drivers: {drivers}." if drivers else "")
        )
    control_text = ""
    if control_posture.get("headline"):
        control_text = f"<br/><br/><b>Control posture</b>: {control_posture.get('headline')}. {control_posture.get('summary', '')}"

    score_data = [[
        Paragraph(f"{deal_score}", ParagraphStyle("Score", fontName="Helvetica-Bold", fontSize=40, textColor=score_color, alignment=TA_CENTER)),
        Paragraph(
            f"<b>PBM Deal Score: {deal_score}/100</b><br/><br/>"
            f"Weighted risk score: {weighted_risk} ({risk_label}). "
            f"This contract has {len(high_flags)} high-severity and {len(medium_flags)} medium-severity flags, "
            f"but the score is weighted toward rebate structure, spread pricing, specialty control, and audit rights."
            f"{'<br/><br/>' + str(methodology) if methodology else ''}"
            f"{override_text}{control_text}",
            styles["Body"],
        ),
    ]]
    score_table = Table(score_data, colWidths=[1.5 * inch, 5 * inch])
    score_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), GRAY_50),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.2 * inch))

    if control_map:
        story.append(Paragraph("Control Map", styles["SubHeader"]))
        control_rows = [["Lever", "Controller", "Assessment", "Implication"]]
        for item in control_map[:5]:
            if isinstance(item, dict):
                control_rows.append([
                    str(item.get("lever", "")),
                    str(item.get("controller", "")),
                    Paragraph(str(item.get("assessment", "")), styles["SmallText"]),
                    Paragraph(str(item.get("implication", "")), styles["SmallText"]),
                ])
        if len(control_rows) > 1:
            control_table = Table(control_rows, colWidths=[1.1 * inch, 1.0 * inch, 2.2 * inch, 2.2 * inch])
            control_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(control_table)
            story.append(Spacer(1, 8))

    if benchmark_observations or top_risks:
        story.append(Paragraph("Observations & Recommendations", styles["SubHeader"]))
        observations_to_render = benchmark_observations[:4] if benchmark_observations else []
        if not observations_to_render:
            observations_to_render = [
                {
                    "kind": "consideration",
                    "title": risk.get("title", "Risk"),
                    "severity": risk.get("severity", "medium"),
                    "tier": risk.get("tier", "N/A"),
                    "benchmark_label": "Priority issue",
                    "benchmark": "Tier 1 economics and control drivers outweigh administrative terms.",
                    "benchmark_source": "ClearScript weighted scoring model",
                    "observation": risk.get("why_it_matters", ""),
                    "implication": risk.get("why_it_matters", ""),
                    "recommendation": risk.get("recommendation", ""),
                    "supporting_detail": None,
                }
                for risk in top_risks[:3]
                if isinstance(risk, dict)
            ]
        for observation in observations_to_render:
            if not isinstance(observation, dict):
                continue
            story.append(Paragraph(
                f"<b>{str(observation.get('title', 'Observation'))}</b> "
                f"({str(observation.get('kind', 'consideration')).title()}, Tier {observation.get('tier', 'N/A')}, {str(observation.get('severity', 'medium')).upper()})",
                styles["Body"],
            ))
            story.append(Paragraph(
                f"<b>Benchmark:</b> {observation.get('benchmark_label', '')}. {observation.get('benchmark', '')}",
                styles["SmallText"],
            ))
            if observation.get("benchmark_source"):
                story.append(Paragraph(f"<b>Source:</b> {observation.get('benchmark_source')}", styles["SmallText"]))
            story.append(Paragraph(f"<b>Observation:</b> {observation.get('observation', '')}", styles["Body"]))
            story.append(Paragraph(f"<b>Implication:</b> {observation.get('implication', '')}", styles["Body"]))
            if observation.get("supporting_detail"):
                story.append(Paragraph(f"<b>Supporting detail:</b> {observation.get('supporting_detail')}", styles["SmallText"]))
            if observation.get("recommendation"):
                story.append(Paragraph(f"<b>Recommendation:</b> {observation.get('recommendation')}", styles["SmallText"]))
            story.append(Spacer(1, 6))

    if financial_exposure:
        story.append(Paragraph("Supporting Leakage Estimates", styles["SubHeader"]))
        if financial_exposure.get("summary"):
            story.append(Paragraph(str(financial_exposure.get("summary")), styles["Body"]))
        exposure_rows = [["Area", "Level", "Directional Exposure", "Driver"]]
        for label, key in [
            ("Rebate Leakage", "rebate_leakage"),
            ("Spread Exposure", "spread_exposure"),
            ("Specialty Control", "specialty_control"),
        ]:
            item = financial_exposure.get(key)
            if isinstance(item, dict):
                exposure_rows.append([
                    label,
                    str(item.get("level", "")).upper(),
                    str(item.get("estimate", "")),
                    Paragraph(str(item.get("driver", "")), styles["SmallText"]),
                ])
        if len(exposure_rows) > 1:
            exposure_table = Table(exposure_rows, colWidths=[1.4 * inch, 0.8 * inch, 1.4 * inch, 3.0 * inch])
            exposure_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(exposure_table)
            story.append(Spacer(1, 8))

    if audit_implication:
        story.append(Paragraph("Audit Interpretation", styles["SubHeader"]))
        story.append(Paragraph(str(audit_implication), styles["Body"]))
        story.append(Spacer(1, 8))

    # ─── 2. Contract Terms ───────────────────────────────────────────────

    story.append(Paragraph("2. Extracted Contract Terms", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

    term_labels = {
        "rebate_passthrough": "Rebate Passthrough",
        "spread_pricing": "Spread Pricing",
        "formulary_clauses": "Formulary Management",
        "audit_rights": "Audit Rights",
        "mac_pricing": "MAC Pricing",
        "termination_provisions": "Termination",
        "gag_clauses": "Gag Clauses",
        "specialty_channel": "Specialty Channel",
    }

    term_rows = [["Term", "Value", "Status", "Details"]]
    if isinstance(analysis, dict):
        for key, label in term_labels.items():
            val = analysis.get(key)
            if not val or not isinstance(val, dict):
                continue
            # Extract the most meaningful value
            display_val = (
                val.get("effective_passthrough")
                or val.get("percentage")
                or val.get("caps")
                or val.get("scope")
                or val.get("notice_period")
                or (str(val.get("notice_days", "")) + " days" if val.get("notice_days") else None)
                or val.get("mechanism")
                or (str(val.get("change_notification_days", "")) + " days" if val.get("change_notification_days") else None)
                or ("Found" if val.get("found") else "Not found")
            )
            details = val.get("details", "")
            favorability = val.get("favorability", "")
            if favorability == "employer_favorable":
                status_label = "EMPLOYER"
                status_key = "good"
            elif favorability == "pbm_favorable":
                status_label = "PBM"
                status_key = "critical"
            elif favorability == "neutral":
                status_label = "NEUTRAL"
                status_key = "warning"
            else:
                has_issue = any(w in str(details).lower() for w in ["no ", "not ", "narrow", "limit", "restrict", "retain"])
                status_label = "PBM" if has_issue else "EMPLOYER"
                status_key = "critical" if has_issue else "good"
            term_rows.append([
                Paragraph(label, styles["Body"]),
                Paragraph(str(display_val)[:60], styles["Body"]),
                Paragraph(status_label, styles[_status_style(status_key, styles)]),
                Paragraph(str(details)[:120], styles["SmallText"]),
            ])

    if len(term_rows) > 1:
        terms_table = Table(term_rows, colWidths=[1.3 * inch, 1.3 * inch, 0.7 * inch, 3.3 * inch])
        terms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
            ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(terms_table)
    else:
        story.append(Paragraph("No contract terms were extracted. Ensure the uploaded document is a valid PBM contract.", styles["Body"]))

    story.append(Spacer(1, 0.2 * inch))

    # ─── 3. Audit Rights Scorecard ───────────────────────────────────────

    if audit_benchmark:
        story.append(Paragraph("3. Audit Rights Scorecard", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        ab_score = audit_benchmark.get("score", 0)
        ab_grade = audit_benchmark.get("grade", "N/A")
        story.append(Paragraph(
            f"<b>Score: {ab_score}/100 (Grade: {ab_grade})</b> — "
            f"{audit_benchmark.get('assessment', '')}",
            styles["Body"],
        ))
        story.append(Spacer(1, 8))

        provisions = audit_benchmark.get("provisions", [])
        if provisions:
            checklist_rows = [["#", "Audit Right", "Status"]]
            for i, p in enumerate(provisions, 1):
                present = p.get("present", False)
                checklist_rows.append([
                    str(i),
                    Paragraph(p.get("item", ""), styles["Body"]),
                    Paragraph("FOUND" if present else "MISSING", styles[_status_style("found" if present else "missing", styles)]),
                ])

            checklist_table = Table(checklist_rows, colWidths=[0.4 * inch, 5 * inch, 1.2 * inch])
            checklist_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(checklist_table)

        story.append(Spacer(1, 0.2 * inch))

    # ─── 4. Compliance Flags ─────────────────────────────────────────────

    if compliance_flags:
        story.append(Paragraph("4. Compliance Flags", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        flag_rows = [["Severity", "Flag", "Recommendation"]]
        for flag in compliance_flags:
            if not isinstance(flag, dict):
                continue
            sev = flag.get("severity", "medium").upper()
            flag_rows.append([
                Paragraph(sev, styles[_status_style(flag.get("severity", "medium"), styles)]),
                Paragraph(flag.get("flag", flag.get("issue", "")), styles["Body"]),
                Paragraph(flag.get("recommendation", flag.get("details", "")), styles["SmallText"]),
            ])

        if len(flag_rows) > 1:
            flags_table = Table(flag_rows, colWidths=[0.9 * inch, 2.8 * inch, 2.9 * inch])
            flags_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(flags_table)

        story.append(Spacer(1, 0.2 * inch))

    # ─── 5. Recommended Contract Redlines ────────────────────────────────

    redlines = analysis.get("redline_suggestions", []) if isinstance(analysis, dict) else []
    if redlines:
        story.append(PageBreak())
        story.append(Paragraph("5. Recommended Contract Redlines", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))
        story.append(Paragraph(
            "The following redline suggestions provide specific replacement language for PBM-favorable contract terms. "
            "Language is sourced from gold-standard state PBM contracts and ERISA best practices.",
            styles["Body"],
        ))
        story.append(Spacer(1, 8))

        for i, redline in enumerate(redlines):
            if not isinstance(redline, dict):
                continue

            # Section header
            story.append(Paragraph(
                f"<b>{redline.get('section', f'Redline {i+1}')}</b>"
                f"{'  [' + redline.get('impact', '').upper() + ' IMPACT]' if redline.get('impact') else ''}",
                styles["SubHeader"],
            ))

            # Current language (strikethrough effect via red color)
            current = redline.get("current_language", "")
            if current:
                story.append(Paragraph("<b>REMOVE:</b>", ParagraphStyle("RedLabel", fontName="Helvetica-Bold", fontSize=8, textColor=RED)))
                current_table = Table([[Paragraph(current, ParagraphStyle("RedText", fontName="Helvetica", fontSize=9, textColor=RED, leading=13))]])
                current_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(current_table)
                story.append(Spacer(1, 4))

            # Suggested language
            suggested = redline.get("suggested_language", "")
            if suggested:
                story.append(Paragraph("<b>REPLACE WITH:</b>", ParagraphStyle("GreenLabel", fontName="Helvetica-Bold", fontSize=8, textColor=EMERALD)))
                suggested_table = Table([[Paragraph(suggested, ParagraphStyle("GreenText", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#065f46"), leading=13))]])
                suggested_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(suggested_table)
                story.append(Spacer(1, 4))

            # Rationale
            rationale = redline.get("rationale", "")
            source = redline.get("source", "")
            if rationale:
                story.append(Paragraph(f"<b>Why:</b> {rationale}", styles["SmallText"]))
            if source:
                story.append(Paragraph(f"<b>Source:</b> {source}", styles["SmallText"]))

            story.append(Spacer(1, 12))

    # ─── 6. Plan Document Benefits (if provided) ────────────────────────

    if plan_benefits and isinstance(plan_benefits, dict):
        section_num = 6
        story.append(PageBreak())
        story.append(Paragraph(f"{section_num}. Plan Document Benefits", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        plan_info = plan_benefits.get("plan_info", {})
        if plan_info:
            info_text = []
            for k in ["plan_name", "carrier", "plan_type", "effective_date"]:
                v = plan_info.get(k)
                if v:
                    info_text.append(f"<b>{k.replace('_', ' ').title()}:</b> {v}")
            if info_text:
                story.append(Paragraph(" &nbsp;|&nbsp; ".join(info_text), styles["Body"]))
                story.append(Spacer(1, 8))

        benefit_rows = [["Benefit", "In-Network", "Out-of-Network"]]
        ded = plan_benefits.get("deductible", {})
        oop = plan_benefits.get("out_of_pocket_maximum", {})
        copays = plan_benefits.get("copays", {})

        if ded:
            benefit_rows.append(["Deductible (Individual)", ded.get("individual_in_network", "N/A"), ded.get("individual_out_of_network", "N/A")])
            benefit_rows.append(["Deductible (Family)", ded.get("family_in_network", "N/A"), ded.get("family_out_of_network", "N/A")])
        if oop:
            benefit_rows.append(["OOP Max (Individual)", oop.get("individual_in_network", "N/A"), oop.get("individual_out_of_network", "N/A")])
        if copays:
            for k, v in copays.items():
                if k != "notes" and v:
                    benefit_rows.append([k.replace("_", " ").title(), str(v), "—"])

        if len(benefit_rows) > 1:
            ben_table = Table(benefit_rows, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
            ben_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(ben_table)

    # ─── 6. Cross-Reference (if provided) ────────────────────────────────

    if cross_reference and isinstance(cross_reference, dict):
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("7. Contract vs Plan Document Cross-Reference", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        alignment = cross_reference.get("overall_alignment_score", 0)
        story.append(Paragraph(
            f"<b>Alignment Score: {alignment}%</b> — {cross_reference.get('summary', '')}",
            styles["Body"],
        ))
        story.append(Spacer(1, 8))

        findings = cross_reference.get("findings", [])
        if findings:
            xref_rows = [["Severity", "Finding", "Recommendation"]]
            for f in findings:
                if not isinstance(f, dict):
                    continue
                xref_rows.append([
                    Paragraph(f.get("severity", "").upper(), styles[_status_style(f.get("severity", ""), styles)]),
                    Paragraph(f.get("finding", ""), styles["Body"]),
                    Paragraph(f.get("recommendation", ""), styles["SmallText"]),
                ])

            if len(xref_rows) > 1:
                xref_table = Table(xref_rows, colWidths=[0.9 * inch, 2.8 * inch, 2.9 * inch])
                xref_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                    ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(xref_table)

        action_items = cross_reference.get("action_items", [])
        if action_items:
            story.append(Spacer(1, 12))
            story.append(Paragraph("Action Items", styles["SubHeader"]))
            for item in action_items:
                if isinstance(item, dict):
                    priority = item.get("priority", "").upper()
                    story.append(Paragraph(
                        f"<b>[{priority}]</b> {item.get('action', '')} — <i>{item.get('reason', '')}</i>",
                        styles["Body"],
                    ))

    # ─── 7. Audit Letter (if provided) ───────────────────────────────────

    if audit_letter:
        story.append(PageBreak())
        story.append(Paragraph("Draft Audit Request Letter", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        for para in str(audit_letter).split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para.replace("\n", "<br/>"), styles["Body"]))
                story.append(Spacer(1, 4))

    # ─── 8. Compliance Deadlines (if provided) ───────────────────────────

    if compliance_deadlines and isinstance(compliance_deadlines, list):
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("Upcoming Compliance Deadlines", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=12))

        dl_rows = [["Regulation", "Date", "Status"]]
        for dl in compliance_deadlines[:10]:
            if isinstance(dl, dict):
                dl_rows.append([
                    str(dl.get("regulation", dl.get("name", "")))[:50],
                    str(dl.get("date", dl.get("deadline", "")))[:20],
                    str(dl.get("status", "")).upper()[:15],
                ])

        if len(dl_rows) > 1:
            dl_table = Table(dl_rows, colWidths=[3.5 * inch, 1.5 * inch, 1.5 * inch])
            dl_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(dl_table)

    # ─── Footer ──────────────────────────────────────────────────────────

    story.append(Spacer(1, 0.5 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=8))
    story.append(Paragraph(
        f"Generated by ClearScript Plan Intelligence &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d')} &nbsp;|&nbsp; clearscript.com",
        styles["Footer"],
    ))
    story.append(Paragraph(
        "This report is generated by AI analysis and should be reviewed by a qualified benefits consultant or ERISA attorney before taking action.",
        styles["Footer"],
    ))

    # Build
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info(f"Generated PDF report: {len(pdf_bytes)} bytes")
    return pdf_bytes

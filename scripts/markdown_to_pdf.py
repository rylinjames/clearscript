"""
Tiny markdown -> branded PDF converter for the ClearScript beta package.

Reuses the brand colors from services/pdf_report_service.py so the artifacts
in the beta package look like they came from the same firm.

Supported markdown subset (deliberately small):
  # heading 1   → BrandTitle + horizontal rule
  ## heading 2  → SectionHeader
  ### heading 3 → SubHeader
  - bullets     → "•" prefixed indented paragraphs (NOT ListFlowable —
                  it has weird spacing on multi-line items)
  | tables |    → reportlab Table with explicit column widths
  **bold**      → <b></b>
  *italic*      → <i></i>
  ---           → horizontal rule
  blank line    → paragraph break

Run from the repo root:
    py scripts/markdown_to_pdf.py docs/beta/Foo.md docs/beta/Bar.md
"""
import re
import sys
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

# Register Bitstream Vera Sans (TTF, bundled with reportlab) as our brand font.
# The default Helvetica is a Type 1 PostScript font with no Unicode support —
# em-dashes and bullets render as CID glyphs that look wrong visually and
# break text extraction. Vera Sans has the full Latin-1 + General Punctuation
# range we need for "—", "•", "✓", smart quotes, etc.
_FONT_DIR = Path(reportlab.__path__[0]) / "fonts"
pdfmetrics.registerFont(TTFont("BrandSans", str(_FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("BrandSans-Bold", str(_FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFont(TTFont("BrandSans-Italic", str(_FONT_DIR / "VeraIt.ttf")))
pdfmetrics.registerFont(TTFont("BrandSans-BoldItalic", str(_FONT_DIR / "VeraBI.ttf")))
pdfmetrics.registerFontFamily(
    "BrandSans",
    normal="BrandSans",
    bold="BrandSans-Bold",
    italic="BrandSans-Italic",
    boldItalic="BrandSans-BoldItalic",
)

# Brand — kept in sync with backend/services/pdf_report_service.py
NAVY = colors.HexColor("#1e3a5f")
GRAY_100 = colors.HexColor("#f4f4f5")
GRAY_200 = colors.HexColor("#e4e4e7")
GRAY_500 = colors.HexColor("#71717a")
GRAY_700 = colors.HexColor("#3f3f46")
GRAY_900 = colors.HexColor("#18181b")

PAGE_W, PAGE_H = letter
USABLE_W = PAGE_W - 1.5 * inch  # left+right margins of 0.75" each


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1", parent=base["Title"], fontName="BrandSans-Bold",
            fontSize=22, textColor=NAVY, leading=26, spaceAfter=2, alignment=0,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="BrandSans-Bold",
            fontSize=13, textColor=NAVY, leading=16, spaceBefore=16, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontName="BrandSans-Bold",
            fontSize=11, textColor=GRAY_700, leading=14, spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="BrandSans",
            fontSize=10, textColor=GRAY_900, leading=14, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"], fontName="BrandSans",
            fontSize=10, textColor=GRAY_900, leading=14,
            leftIndent=18, firstLineIndent=-10, spaceAfter=4,
            bulletIndent=8,
        ),
    }


def _inline(text: str) -> str:
    """Apply inline markdown (**bold**, *italic*) and escape angle brackets."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _parse_table(lines: list[str], start: int) -> tuple[Table, int]:
    """Parse a markdown pipe table starting at lines[start]. Returns (Table, next_index)."""
    s = _styles()
    rows: list[list[Paragraph]] = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        raw = lines[i].strip().strip("|")
        cells = [c.strip() for c in raw.split("|")]
        if not all(re.fullmatch(r":?-+:?", c) for c in cells):
            rows.append([Paragraph(_inline(c), s["body"]) for c in cells])
        i += 1
    if not rows:
        return None, i

    n_cols = len(rows[0])
    col_w = USABLE_W / n_cols
    table = Table(rows, colWidths=[col_w] * n_cols, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_100),
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, GRAY_200),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table, i


def md_to_story(md_text: str) -> list:
    """Walk the markdown line-by-line and emit reportlab flowables."""
    s = _styles()
    story: list = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line — handled by Paragraph spaceAfter, just advance
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(
                width="100%", thickness=0.75, color=GRAY_200, spaceAfter=10
            ))
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            story.append(Paragraph(_inline(stripped[2:]), s["h1"]))
            story.append(HRFlowable(
                width="100%", thickness=2, color=NAVY,
                spaceBefore=2, spaceAfter=14
            ))
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(_inline(stripped[3:]), s["h2"]))
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(_inline(stripped[4:]), s["h3"]))
            i += 1
            continue

        # Tables
        if stripped.startswith("|"):
            table, i = _parse_table(lines, i)
            if table is not None:
                story.append(table)
                story.append(Spacer(1, 10))
            continue

        # Bullets — render inline as paragraphs with a bullet prefix.
        # ListFlowable produces inconsistent indentation on multi-line items
        # so we render bullets manually.
        if stripped.startswith("- "):
            # Collect a contiguous run of bullets so we can group them
            bullet_items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                # Allow continuation lines that are indented more than 2 spaces
                content = lines[i].strip()[2:]
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if nxt.startswith("  ") and not nxt.strip().startswith("-"):
                        content += " " + nxt.strip()
                        j += 1
                    else:
                        break
                bullet_items.append(content)
                i = j
            for item in bullet_items:
                p = Paragraph("•&nbsp;&nbsp;" + _inline(item), s["bullet"])
                story.append(p)
            story.append(Spacer(1, 4))
            continue

        # Plain paragraph — collect contiguous non-blank, non-special lines
        para_lines = [stripped]
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if not nxt:
                break
            if nxt.startswith(("#", "-", "|", "---")):
                break
            para_lines.append(nxt)
            j += 1
        story.append(Paragraph(_inline(" ".join(para_lines)), s["body"]))
        i = j

    return story


def render(md_path: Path, pdf_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=md_path.stem.replace("_", " "),
        author="ClearScript",
    )
    doc.build(md_to_story(md_text))
    print(f"Wrote {pdf_path} ({pdf_path.stat().st_size:,} bytes)")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: markdown_to_pdf.py <input.md> [input2.md ...]")
    for arg in sys.argv[1:]:
        md_path = Path(arg)
        pdf_path = md_path.with_suffix(".pdf")
        render(md_path, pdf_path)


if __name__ == "__main__":
    main()

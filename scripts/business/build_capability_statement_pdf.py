#!/usr/bin/env python3
"""Generate the SCBE-AETHERMOORE capability statement PDF.

Single-page Letter with two-column header, sectioned bullets, NAICS/PSC
side-by-side, and a POC footer. Uses ReportLab so no browser/Chromium is
needed. Output: docs/business/CAPABILITY_STATEMENT.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "business" / "CAPABILITY_STATEMENT.pdf"

NAVY = HexColor("#0b2545")
SLATE = HexColor("#4a5a73")
LIGHT_BG = HexColor("#f3f5f8")
RULE_LIGHT = HexColor("#c8d2e0")

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=NAVY,
    spaceAfter=2,
)
tagline_style = ParagraphStyle(
    "Tagline",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10.5,
    leading=13,
    textColor=SLATE,
    spaceAfter=8,
)
section_style = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=NAVY,
    spaceBefore=8,
    spaceAfter=3,
)
body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=12.5,
    textColor=HexColor("#111111"),
    leftIndent=10,
    spaceAfter=1,
)
header_label_style = ParagraphStyle(
    "HdrLabel",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=12.5,
    textColor=HexColor("#111111"),
)
footer_style = ParagraphStyle(
    "Footer",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13.5,
    textColor=HexColor("#111111"),
)
footer_strong_style = ParagraphStyle(
    "FooterStrong",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13.5,
    textColor=NAVY,
)


def bullet(text: str):
    return Paragraph("- " + text, body_style)


def label_value(label: str, value: str):
    return Paragraph(
        f'<font color="#4a5a73"><b>{label}:</b></font> {value}',
        header_label_style,
    )


def section_header(text: str):
    para = Paragraph(text.upper(), section_style)
    tbl = Table([[para]], colWidths=[7.0 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.6, RULE_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return tbl


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="SCBE-AETHERMOORE Capability Statement",
        author="Issac D. Davis",
    )

    story = []

    title_tbl = Table(
        [[Paragraph("SCBE-AETHERMOORE", title_style)]],
        colWidths=[7.3 * inch],
    )
    title_tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 2.5, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(title_tbl)
    story.append(
        Paragraph(
            "AI Safety, Governance, and Risk-Mitigation Engineering for Federal Mission Systems",
            tagline_style,
        )
    )

    left_col = [
        label_value("Principal", "Issac D. Davis"),
        label_value("Address", "2361 East 5th Avenue, Port Angeles, WA 98362"),
        label_value("Email", "issdandavis7795@gmail.com"),
        label_value("Phone", "(360) 808-0876"),
        label_value("Website", "https://aethermoore.com"),
    ]
    right_col = [
        label_value("UEI", "J4NXHM6N5F59"),
        label_value("CAGE Code", "1EXD5"),
        label_value("SAM Status", "Active (registered 2026-04-02; expires 2027-04-03)"),
        label_value("SBA SBIR ID", "SBC_002676728"),
        label_value("Business Type", "Sole Proprietor, Minority-Owned Small Business"),
    ]
    hdr_tbl = Table(
        [[left_col, right_col]],
        colWidths=[3.55 * inch, 3.55 * inch],
    )
    hdr_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(hdr_tbl)

    story.append(section_header("Core Competencies"))
    for item in [
        "AI safety, governance, and risk-mitigation engineering",
        "AI compliance and audit tooling (model behavior testing, red-team harnesses, output monitoring)",
        "Responsible AI deployment advisory and integration",
        "Prompt-injection and model-misuse defense",
        "AI legal/regulatory exposure reduction (NIST AI RMF-aligned, EO 14110-aware)",
        "Custom AI tooling and integration for federal mission systems",
    ]:
        story.append(bullet(item))

    story.append(section_header("Differentiators"))
    for item in [
        "Founder-led, low-overhead delivery; direct technical engagement, no layered subcontracting",
        "Specialized focus on failure modes federal AI deployments most often miss: legal exposure, oversight gaps, and unsafe output handling",
        "Rapid prototyping of governance tooling tailored to agency-specific data and policy environments",
        "Minority-owned small business - supports agency small-business and socioeconomic goals",
    ]:
        story.append(bullet(item))

    naics_items = [
        "541511 - Custom Computer Programming Services",
        "541512 - Computer Systems Design Services",
        "541519 - Other Computer Related Services",
        "541611 - Admin &amp; General Mgmt Consulting",
        "541690 - Other Scientific &amp; Technical Consulting",
        "541715 - R&amp;D in Physical, Engineering, Life Sciences",
        "611430 - Professional &amp; Mgmt Development Training",
    ]
    psc_items = [
        "DA01 / DA10 - IT and Telecom Services",
        "R408 - Program Management/Support Services",
        "R425 - Engineering and Technical Services",
        "AJ11 - R&amp;D - General Science/Tech (Applied Research)",
    ]

    def code_block(title: str, items: list[str]):
        inner = [section_header(title)]
        inner.extend(bullet(it) for it in items)
        return inner

    code_tbl = Table(
        [[code_block("NAICS Codes", naics_items), code_block("PSC Codes", psc_items)]],
        colWidths=[3.55 * inch, 3.55 * inch],
    )
    code_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(code_tbl)

    story.append(section_header("Capability Areas"))
    for item in [
        "AI risk assessment and governance framework design",
        "LLM safety evaluation tooling",
        "Compliance documentation aligned to NIST AI RMF, ISO/IEC 42001, and federal AI directives",
        "AI-related legal exposure analysis and mitigation playbooks",
    ]:
        story.append(bullet(item))

    story.append(Spacer(1, 0.1 * inch))
    poc_rows = [
        [Paragraph("Point of Contact", footer_strong_style)],
        [Paragraph("Issac D. Davis, Principal", footer_style)],
        [Paragraph("issdandavis7795@gmail.com &nbsp;-&nbsp; (360) 808-0876", footer_style)],
    ]
    poc_tbl = Table(poc_rows, colWidths=[7.3 * inch])
    poc_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("LINEBEFORE", (0, 0), (-1, -1), 3, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
            ]
        )
    )
    story.append(poc_tbl)

    doc.build(story)
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"OK: {out} ({out.stat().st_size:,} bytes)")

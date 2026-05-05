#!/usr/bin/env python3
"""Build PDF for the DHS S&T AI/ML/DS Sources Sought response (70RSAT26RFI000015).

Multi-page Letter document; sections + paragraphs + bullet lists + a
header table. Mirrors docs/business/responses/DHS_ST_AIMLDS_70RSAT26RFI000015.md.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "business" / "responses" / "DHS_ST_AIMLDS_70RSAT26RFI000015.pdf"

NAVY = HexColor("#0b2545")
SLATE = HexColor("#4a5a73")
LIGHT_BG = HexColor("#f3f5f8")
RULE_LIGHT = HexColor("#c8d2e0")
INK = HexColor("#111111")

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=14.5,
    leading=18,
    textColor=NAVY,
    spaceAfter=2,
)
subtitle_style = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=SLATE,
    spaceAfter=6,
)
section_style = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=NAVY,
    spaceBefore=8,
    spaceAfter=3,
)
subsection_style = ParagraphStyle(
    "Subsection",
    parent=styles["Heading3"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=NAVY,
    spaceBefore=6,
    spaceAfter=2,
)
body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13.5,
    textColor=INK,
    spaceAfter=4,
    alignment=4,  # justify
)
bullet_style = ParagraphStyle(
    "Bullet",
    parent=body_style,
    leftIndent=14,
    spaceAfter=1,
    alignment=0,
)
small_style = ParagraphStyle(
    "Small",
    parent=body_style,
    fontSize=9,
    leading=12,
    textColor=SLATE,
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


def bullet(text: str):
    return Paragraph("- " + text, bullet_style)


def kv_table(rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", body_style), Paragraph(v, body_style)] for k, v in rows]
    tbl = Table(data, colWidths=[1.6 * inch, 5.5 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE_LIGHT),
            ]
        )
    )
    return tbl


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Response to Sources Sought 70RSAT26RFI000015",
        author="Issac D. Davis (SCBE-AETHERMOORE)",
    )
    story = []

    # Title block
    story.append(Paragraph("SCBE-AETHERMOORE", title_style))
    story.append(
        Paragraph(
            "Response to Sources Sought / RFI 70RSAT26RFI000015 &middot; "
            "Artificial Intelligence, Machine Learning, and Data Science (AI/ML/DS) "
            "Technical Support Services &middot; DHS S&amp;T",
            subtitle_style,
        )
    )

    story.append(
        kv_table(
            [
                ("Issuing office", "DHS S&amp;T &mdash; Office of Procurement Operations, Sci Tech Acq Division"),
                ("RFI POC", "Jennifer K. Koons &mdash; Jennifer.Koons@hq.dhs.gov"),
                ("Response date", "2026-05-05"),
                ("Submitted by", "SCBE-AETHERMOORE (Issac D. Davis, sole proprietor)"),
                ("Attached", "SCBE-AETHERMOORE Capability Statement (1 page)"),
            ]
        )
    )

    # 1. Company Identification
    story.append(section_header("1. Company Identification"))
    story.append(
        kv_table(
            [
                ("Legal name", "Issac D. Davis (DBA SCBE-AETHERMOORE)"),
                ("UEI", "J4NXHM6N5F59"),
                ("CAGE Code", "1EXD5"),
                ("SAM status", "Active (registered 2026-04-02; expires 2027-04-03)"),
                ("SBA SBIR ID", "SBC_002676728"),
                ("Business size", "Small business under all listed NAICS, including 541611"),
                ("Socioeconomic", "Sole proprietor; minority-owned"),
                ("Address", "2361 East 5th Avenue, Port Angeles, WA 98362"),
                ("Phone", "(360) 808-0876"),
                ("Email", "issdandavis7795@gmail.com"),
                ("Website", "https://aethermoore.com"),
                ("GitHub", "https://github.com/issdandavis/SCBE-AETHERMOORE"),
            ]
        )
    )

    # 2. Capability Mapping
    story.append(section_header("2. Capability Mapping to the RFI Statement of Need"))
    story.append(
        Paragraph(
            "The RFI lists six technical capability areas. Below is an honest yes / partial / no map "
            "against each, followed by evidence.",
            body_style,
        )
    )

    cap_blocks = [
        (
            "2.1 Conducting and providing independent evaluations of AI/ML/DS tools &mdash; YES",
            [
                "SCBE-AETHERMOORE's primary practice area is independent, gate-based evaluation of AI/ML systems. "
                "Our open-source repository implements:",
            ],
            [
                "A multi-layer safety pipeline (governance, harmonic, constrained-decoding) that scores model "
                "outputs against frozen contracts.",
                "A double-blind evaluation harness with cryptographic commit-reveal mapping receipts, so candidate "
                "identity is hidden from the scoring stage and tampering is mathematically detectable.",
                "An executable promotion gate that blocks model promotion when frozen-holdout benchmarks fail "
                '&mdash; no metric-only "passes."',
            ],
            "These are exactly the tools required when an agency needs an evaluator that is not the system vendor.",
        ),
        (
            "2.2 Supporting testing, validation, and standards development &mdash; YES",
            ["We design test contracts shaped against:"],
            [
                "NIST AI Risk Management Framework (AI RMF 1.0) &mdash; Govern, Map, Measure, Manage functions",
                "ISO/IEC 42001:2023 AI management system controls",
                "EO 14110 federal AI deployment guidance",
            ],
            "Our compliance documentation pattern is reusable across mission domains: required-token contracts, "
            "forbidden-token boundary guards, must-pass thresholds, and reproducible scoring receipts.",
        ),
        (
            "2.3 Evaluating and analyzing AI/ML and DS tools &mdash; YES",
            [
                "We perform tooling-side evaluations: comparing model behavior across base models, adapters, and "
                "decoding strategies; isolating which intervention (training vs. constrained decoding vs. prompt "
                "design) actually moves the gate metric. We have published failure-mode postmortems where SFT "
                "plateaued and constrained decoding cleared the same gate at 5/5 &mdash; a class of finding that "
                "materially changes evaluator recommendations.",
            ],
            [],
            "",
        ),
        (
            "2.4 Developing and evaluating automated image analysis software and algorithms &mdash; PARTIAL",
            [
                "This is not our primary practice area. We have not built production image-analysis pipelines for "
                "X-ray or CT screening data. We can credibly support the evaluation, governance, and assurance "
                "layer above an image-analysis tool &mdash; including bias and drift detection, threshold "
                "calibration, and adversarial robustness testing &mdash; but we would not lead the model-development "
                "side without a teaming partner who specializes in computer vision for screening.",
            ],
            [],
            "",
        ),
        (
            "2.5 Supporting development and interpretation of open architecture data and metadata standards &mdash; YES",
            [
                "We maintain machine-readable schemas and JSONL contract formats for AI evaluation, training data, "
                "and audit telemetry. Our work emphasizes deterministic, version-pinned schemas that survive model "
                "and tool churn &mdash; exactly the property an open-architecture standard needs.",
            ],
            [],
            "",
        ),
        (
            "2.6 Supporting and creating algorithm training, validation, testing and assurance tools &mdash; YES",
            [
                "We build assurance tooling end to end: training-data validation, post-training evaluation gates, "
                "tamper-resistant scoring, and audit-grade reporting. Our recent published work demonstrates the "
                "full loop on a 0.5B-parameter chemistry-verification adapter, including a post-train gate runner "
                "that exits non-zero on threshold miss before any model is promoted. The same harness generalizes "
                "to any required/forbidden contract &mdash; including image-analysis output validation when the "
                "relevant labels are tokenizable.",
            ],
            [],
            "",
        ),
    ]

    for header, intro_paras, bullets, closing in cap_blocks:
        block = [Paragraph(header, subsection_style)]
        for p in intro_paras:
            block.append(Paragraph(p, body_style))
        for b in bullets:
            block.append(bullet(b))
        if closing:
            block.append(Paragraph(closing, body_style))
        story.append(KeepTogether(block))

    # 3. Differentiators
    story.append(section_header("3. Key Differentiators"))
    for item in [
        "<b>Founder-led delivery, no subcontracting layers.</b> Direct technical engagement; rapid iteration; "
        "cost discipline appropriate to RFIs and Phase I-scale work.",
        "<b>Open public artifact of capability.</b> Our governance, evaluation, and assurance code is on GitHub "
        "today (https://github.com/issdandavis/SCBE-AETHERMOORE), with a documented commit history, CI gates, "
        "and reproducible test suites. DHS S&amp;T evaluators can inspect the actual work product before contracting.",
        "<b>Minority-owned small business.</b> Supports DHS small-business and socioeconomic goals; eligible for "
        "relevant set-asides under listed NAICS.",
        "<b>Active in adjacent federal AI/safety pipelines.</b> Submitted abstract to DARPA MATHBAC "
        "(DARPA-SN-26-59) and proposal to DARPA CLARA (DARPA-PA-25-07-02 / FP-033) &mdash; June 2026 award "
        "decisions. Demonstrates the firm's federal-research engagement is real, not aspirational.",
    ]:
        story.append(bullet(item))

    # 4. Past Performance
    story.append(section_header("4. Past Performance"))
    story.append(
        Paragraph(
            "SCBE-AETHERMOORE is an early-stage small business (SAM-active since 2026-04-02). We have "
            "<b>no prior federal contracts</b>. We are responding because the RFI explicitly requests insight "
            "into small-business capabilities, including emerging firms.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "In lieu of contract past performance, the public technical record stands as primary evidence:",
            body_style,
        )
    )
    for item in [
        "<b>GitHub repository</b> (https://github.com/issdandavis/SCBE-AETHERMOORE) &mdash; multi-language "
        "(TypeScript, Python, Rust) implementation of an AI governance and assurance pipeline, including 14 "
        "documented architectural layers and a continuous-integration test suite.",
        "<b>Documented postmortem of an evaluation cycle</b> &mdash; the firm's discipline on negative results: "
        "failed adapters were not silently dropped; the failure modes were enumerated and a follow-on "
        "intervention (constrained decoding) was empirically validated to clear the original contract gate at 5/5.",
        "<b>Active federal proposal pipeline</b> &mdash; MATHBAC abstract submitted 2026-04-27; DARPA CLARA "
        "FP-033 submitted (decision 2026-06-16).",
    ]:
        story.append(bullet(item))
    story.append(
        Paragraph(
            "We are willing to provide additional technical demonstrations or read-only repository access on request.",
            body_style,
        )
    )

    # 5. Recommended Procurement Approach
    story.append(section_header("5. Recommended Procurement Approach"))
    story.append(
        Paragraph(
            "We respectfully suggest DHS S&amp;T consider the following for the eventual task order:",
            body_style,
        )
    )
    for item in [
        "<b>Total small-business set-aside</b> under NAICS 541611 if the requirement size supports it. The RFI's "
        "stated purpose includes understanding small-business capability specifically; a set-aside aligns means "
        "with end.",
        "<b>OASIS+ Small Business pool</b> as the contract vehicle, consistent with the RFI's market-research "
        "framing. SCBE-AETHERMOORE is not currently an OASIS+ holder, but we can team with an OASIS+ "
        "small-business prime to provide the AI evaluation, governance, and assurance components of the task order.",
        "<b>Modular task structure</b> that separates (a) image-analysis development, (b) evaluation and "
        "assurance, and (c) standards/test-tool development. This lets DHS S&amp;T match each task module to "
        "firms whose capabilities are actually deepest in that module.",
    ]:
        story.append(bullet(item))

    # 6. POC
    story.append(section_header("6. Point of Contact"))
    story.append(
        Paragraph(
            "<b>Issac D. Davis</b><br/>Principal, SCBE-AETHERMOORE<br/>"
            "Email: issdandavis7795@gmail.com<br/>"
            "Phone: (360) 808-0876<br/>"
            "Address: 2361 East 5th Avenue, Port Angeles, WA 98362",
            body_style,
        )
    )

    # 7. Statement of Compliance
    story.append(section_header("7. Statement of Compliance"))
    story.append(Paragraph("This response is submitted in compliance with the RFI:", body_style))
    for item in [
        "This response is <b>not a proposal</b> and does not constitute a binding offer.",
        "No proprietary or restricted information is included; the entire response is releasable.",
        "SCBE-AETHERMOORE acknowledges that the Government will not reimburse any costs incurred in preparing "
        "this response.",
        "All factual claims (UEI, CAGE, SAM status, business size) are verifiable in SAM.gov as of the response date.",
    ]:
        story.append(bullet(item))

    doc.build(story)
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"OK: {out} ({out.stat().st_size:,} bytes)")

"""
Generate USPTO filing package as PDF.
No Word required — uses reportlab.

Creates: Combined_Filing_Package.pdf
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

# ── Applicant Info ──
APPLICANT = {
    "full_name": "Issac Daniel Davis",
    "address": "2361 E 5th Ave",
    "city": "Port Angeles",
    "state": "WA",
    "zip": "98362",
    "country": "US",
    "phone": "360-808-0876",
    "email": "",  # ← ADD YOUR EMAIL
}

APP = {
    "number": "63/961,403",
    "filing_date": "January 15, 2026",
    "title": "Context-Bound Cryptographic Authorization System",
    "docket": "SCBE-2026-001",
    "claims": 16,
    "fee": "$65.00",
}

TODAY = date.today().strftime("%m/%d/%Y")
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "Combined_Filing_Package.pdf")


def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1.2 * inch,
        rightMargin=1.2 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        "DocTitle", parent=styles["Title"],
        fontSize=22, spaceAfter=6, textColor=HexColor("#1a1a1a"),
    ))
    styles.add(ParagraphStyle(
        "SectionHead", parent=styles["Heading1"],
        fontSize=14, spaceBefore=20, spaceAfter=10,
        textColor=HexColor("#1a1a1a"), underline=True,
    ))
    styles.add(ParagraphStyle(
        "SubHead", parent=styles["Heading2"],
        fontSize=12, spaceBefore=14, spaceAfter=8,
        textColor=HexColor("#333333"),
    ))
    styles.add(ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=11, leading=15, spaceBefore=4, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "BodyRight", parent=styles["Normal"],
        fontSize=11, leading=15, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        "BodyCenter", parent=styles["Normal"],
        fontSize=11, leading=15, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "Checkbox", parent=styles["Normal"],
        fontSize=11, leading=15, leftIndent=24, spaceBefore=6, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=HexColor("#666666"),
    ))
    styles.add(ParagraphStyle(
        "Warning", parent=styles["Normal"],
        fontSize=10, leading=13, textColor=HexColor("#b30000"),
        spaceBefore=10,
    ))
    styles.add(ParagraphStyle(
        "SignLine", parent=styles["Normal"],
        fontSize=11, leading=20, spaceBefore=4,
    ))

    S = styles
    elements = []

    def spacer(h=0.15):
        elements.append(Spacer(1, h * inch))

    def hr():
        elements.append(HRFlowable(width="100%", thickness=1,
                                    color=HexColor("#cccccc"),
                                    spaceBefore=8, spaceAfter=8))

    def field_table(rows, col_widths=None):
        if col_widths is None:
            col_widths = [2.2 * inch, 4 * inch]
        t = Table(rows, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#999999")),
            ("BACKGROUND", (0, 0), (0, -1), HexColor("#f5f5f5")),
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
            ("FONT", (1, 0), (1, -1), "Helvetica", 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        spacer(0.15)

    def checkbox(text, checked=True):
        mark = "\u2611" if checked else "\u2610"
        elements.append(Paragraph(f"{mark}  {text}", S["Checkbox"]))

    email_display = APPLICANT["email"] or "(to be provided)"

    # ================================================================
    # TITLE PAGE
    # ================================================================
    spacer(2)
    elements.append(Paragraph("USPTO Filing Package", S["DocTitle"]))
    spacer(0.3)
    elements.append(Paragraph(
        "Response to Notice to File Missing Parts", S["BodyCenter"]))
    spacer(0.5)
    hr()
    spacer(0.3)

    field_table([
        ["Application No.", APP["number"]],
        ["Title", APP["title"]],
        ["Applicant", APPLICANT["full_name"]],
        ["Filing Date", APP["filing_date"]],
        ["Fee Due", f'{APP["fee"]}  (Micro Entity)'],
        ["Deadline", "April 19, 2026"],
        ["Date Prepared", TODAY],
    ])

    spacer(0.5)
    elements.append(Paragraph(
        "<b>Contents:</b><br/>"
        "1. Cover Letter to Commissioner for Patents<br/>"
        "2. PTO/SB/15A — Certification of Micro Entity Status<br/>"
        "3. PTO/SB/16 — Provisional Application Cover Sheet<br/>"
        "4. Filing Checklist &amp; Reference Codes",
        S["Body"],
    ))

    elements.append(PageBreak())

    # ================================================================
    # 1. COVER LETTER
    # ================================================================
    elements.append(Paragraph("1.  Cover Letter", S["SectionHead"]))
    spacer(0.3)

    # Sender block (right-aligned)
    elements.append(Paragraph(
        f"{APPLICANT['full_name']}<br/>"
        f"{APPLICANT['address']}<br/>"
        f"{APPLICANT['city']}, {APPLICANT['state']} {APPLICANT['zip']}<br/>"
        f"Phone: {APPLICANT['phone']}<br/>"
        f"<br/>{TODAY}",
        S["BodyRight"],
    ))
    spacer(0.3)

    # Addressee
    elements.append(Paragraph(
        "Commissioner for Patents<br/>"
        "United States Patent and Trademark Office<br/>"
        "P.O. Box 1450<br/>"
        "Alexandria, VA 22313-1450",
        S["Body"],
    ))
    spacer(0.2)

    elements.append(Paragraph(
        "<b>Re: Response to Notice to File Missing Parts of Application</b>",
        S["Body"],
    ))
    spacer(0.1)

    field_table([
        ["Application Number", APP["number"]],
        ["Filing Date", APP["filing_date"]],
        ["Title of Invention", APP["title"]],
        ["Applicant", APPLICANT["full_name"]],
        ["Docket Number", APP["docket"]],
    ])

    elements.append(Paragraph("Dear Commissioner:", S["Body"]))
    spacer(0.1)

    elements.append(Paragraph(
        "In response to the Notice to File Missing Parts of the "
        "above-identified provisional patent application, the undersigned "
        "applicant respectfully submits the following:",
        S["Body"],
    ))
    spacer(0.1)

    for item in [
        "1.  Certification of Micro Entity Status (PTO/SB/15A) — attached hereto.",
        "2.  Provisional Application Cover Sheet (PTO/SB/16) — attached hereto.",
        f"3.  Filing fee payment of {APP['fee']} (Micro Entity rate) — "
        "submitted via Patent Center electronic payment.",
    ]:
        elements.append(Paragraph(item, S["Body"]))

    spacer(0.1)
    elements.append(Paragraph(
        "The applicant certifies qualification as a Micro Entity under "
        "37 CFR 1.29(a). The required certification form (PTO/SB/15A) is "
        "included with this submission.",
        S["Body"],
    ))
    spacer(0.1)
    elements.append(Paragraph(
        "The applicant respectfully requests that the Office accept this "
        "response and complete processing of the above-identified "
        "provisional patent application.",
        S["Body"],
    ))
    spacer(0.2)
    elements.append(Paragraph("Respectfully submitted,", S["Body"]))
    spacer(0.4)

    elements.append(Paragraph("_" * 50, S["SignLine"]))
    elements.append(Paragraph(APPLICANT["full_name"], S["Body"]))
    elements.append(Paragraph("Pro Se Applicant", S["Body"]))
    elements.append(Paragraph(f"Date: {TODAY}", S["Body"]))
    elements.append(Paragraph(f"Telephone: {APPLICANT['phone']}", S["Body"]))

    elements.append(PageBreak())

    # ================================================================
    # 2. PTO/SB/15A
    # ================================================================
    elements.append(Paragraph(
        "2.  Certification of Micro Entity Status", S["SectionHead"]))
    elements.append(Paragraph(
        "PTO/SB/15A  —  37 CFR 1.29(a) (Gross Income Basis)", S["BodyCenter"]))
    spacer(0.3)

    elements.append(Paragraph("Application Information", S["SubHead"]))
    field_table([
        ["Application Number", APP["number"]],
        ["Filing Date", APP["filing_date"]],
        ["First Named Inventor", APPLICANT["full_name"]],
        ["Title of Invention", APP["title"]],
        ["Docket Number", APP["docket"]],
    ])

    elements.append(Paragraph(
        "Applicant Hereby Certifies the Following:", S["SubHead"]))

    checkbox(
        "The applicant qualifies as a micro entity as defined in "
        "37 CFR 1.29(a)."
    )
    checkbox(
        "Neither the applicant nor the inventor has been named as "
        "inventor on more than four (4) previously filed patent "
        "applications, other than applications filed in another country, "
        "provisional applications under 35 U.S.C. 111(b), or "
        "international applications under 35 U.S.C. 371."
    )
    checkbox(
        "Neither the applicant nor the inventor, in the calendar year "
        "preceding the calendar year in which the applicable fee is being "
        "paid, had a gross income (as defined in section 61(a) of the "
        "Internal Revenue Code of 1986) exceeding three times the median "
        "household income for that preceding calendar year, as most "
        "recently reported by the Bureau of the Census. "
        "(current posted threshold: $251,190.)"
    )
    checkbox(
        "Neither the applicant nor the inventor has assigned, granted, or "
        "conveyed, and is not under an obligation by contract or law to "
        "assign, grant, or convey, a license or other ownership interest "
        "in the application concerned to an entity that had gross income "
        "exceeding three times the median household income."
    )

    spacer(0.2)
    elements.append(Paragraph("Signature", S["SubHead"]))
    field_table([
        ["Signature", f"/{APPLICANT['full_name']}/"],
        ["Name (Printed)", APPLICANT["full_name"]],
        ["Date", TODAY],
        ["Registration No.", "N/A — Pro Se Applicant"],
        ["Telephone", APPLICANT["phone"]],
    ])

    elements.append(Paragraph("Applicant Information", S["SubHead"]))
    field_table([
        ["Name", APPLICANT["full_name"]],
        ["Street Address", APPLICANT["address"]],
        ["City", APPLICANT["city"]],
        ["State", APPLICANT["state"]],
        ["ZIP Code", APPLICANT["zip"]],
        ["Country", APPLICANT["country"]],
        ["Telephone", APPLICANT["phone"]],
        ["Email", email_display],
    ])

    elements.append(Paragraph(
        "<b>WARNING:</b> Improperly claiming micro entity status may "
        "result in the patent being held unenforceable. Applicant "
        "certifies that all statements herein are true and correct.",
        S["Warning"],
    ))

    elements.append(PageBreak())

    # ================================================================
    # 3. PTO/SB/16
    # ================================================================
    elements.append(Paragraph(
        "3.  Provisional Application Cover Sheet", S["SectionHead"]))
    elements.append(Paragraph(
        "PTO/SB/16  —  37 CFR 1.53(c)", S["BodyCenter"]))
    spacer(0.1)
    elements.append(Paragraph(
        "<i>Request for filing a PROVISIONAL APPLICATION FOR PATENT "
        "under 37 CFR 1.53(c).</i>", S["BodyCenter"],
    ))
    spacer(0.3)

    elements.append(Paragraph("Title of Invention", S["SubHead"]))
    elements.append(Paragraph(f"<b>{APP['title']}</b>", S["Body"]))
    spacer(0.2)

    elements.append(Paragraph("Inventor", S["SubHead"]))
    field_table([
        ["Given Name", "Issac Daniel"],
        ["Family Name", "Davis"],
        ["Street Address", APPLICANT["address"]],
        ["City", APPLICANT["city"]],
        ["State", APPLICANT["state"]],
        ["ZIP Code", APPLICANT["zip"]],
        ["Country", APPLICANT["country"]],
    ])

    elements.append(Paragraph("Correspondence Address", S["SubHead"]))
    field_table([
        ["Name", APPLICANT["full_name"]],
        ["Street Address", APPLICANT["address"]],
        ["City", APPLICANT["city"]],
        ["State", APPLICANT["state"]],
        ["ZIP Code", APPLICANT["zip"]],
        ["Country", APPLICANT["country"]],
        ["Telephone", APPLICANT["phone"]],
        ["Email", email_display],
    ])

    elements.append(Paragraph("Entity Status", S["SubHead"]))
    checkbox("Micro Entity (37 CFR 1.29)", checked=True)
    checkbox("Small Entity (37 CFR 1.27)", checked=False)
    checkbox("Regular Undiscounted", checked=False)
    elements.append(Paragraph(
        "<i>PTO/SB/15A (Certification of Micro Entity Status) is attached.</i>",
        S["Body"],
    ))
    spacer(0.2)

    elements.append(Paragraph("Application Details", S["SubHead"]))
    field_table([
        ["Application Number", APP["number"]],
        ["Original Filing Date", APP["filing_date"]],
        ["Number of Claims", str(APP["claims"])],
        ["Docket Number", APP["docket"]],
    ])

    elements.append(Paragraph("Signature", S["SubHead"]))
    field_table([
        ["Signature", f"/{APPLICANT['full_name']}/"],
        ["Name (Printed)", APPLICANT["full_name"]],
        ["Date", TODAY],
        ["Registration No.", "N/A — Pro Se Applicant"],
    ])

    elements.append(PageBreak())

    # ================================================================
    # 4. FILING CHECKLIST & REFERENCE CODES
    # ================================================================
    elements.append(Paragraph(
        "4.  Filing Checklist &amp; Reference Codes", S["SectionHead"]))
    spacer(0.2)

    elements.append(Paragraph(
        "Use this checklist when filing at patentcenter.uspto.gov:",
        S["Body"],
    ))
    spacer(0.1)

    steps = [
        "Log in to Patent Center (patentcenter.uspto.gov)",
        f"Navigate to application {APP['number']}",
        "Select 'File a Document' or 'Follow-on Submissions'",
        "Upload this Cover Letter (Section 1)",
        "Upload PTO/SB/15A — Micro Entity Certification (Section 2)",
        "Upload PTO/SB/16 — Cover Sheet (Section 3)",
        "Select entity status: Micro Entity",
        f"Verify fee amount shows {APP['fee']}",
        "Enter payment information (credit/debit card)",
        "Submit payment",
        "Save confirmation receipt / screenshot",
        "Verify submission shows 'Received' the next business day",
    ]
    for i, step in enumerate(steps, 1):
        checkbox(f"Step {i}: {step}", checked=False)

    spacer(0.3)
    elements.append(Paragraph(
        "<b>USPTO Customer Service:</b>  1-800-786-9199", S["Body"]))

    spacer(0.3)
    elements.append(Paragraph("Reference Codes", S["SubHead"]))
    field_table([
        ["PTO/SB/15A", "Certification of Micro Entity Status (37 CFR 1.29)"],
        ["PTO/SB/16", "Provisional Cover Sheet (37 CFR 1.53(c))"],
        ["37 CFR 1.29", "Micro Entity definition and requirements"],
        ["37 CFR 1.29(a)", "Gross Income Basis for Micro Entity"],
        ["37 CFR 1.53(c)", "Provisional application filing requirements"],
        ["35 U.S.C. 111(b)", "Provisional patent application statute"],
        ["35 U.S.C. 119(e)", "Priority claim from provisional"],
        ["MPEP 509.04", "Micro Entity status guidance"],
        ["Fee Code 1005", "Provisional filing fee — Micro Entity"],
    ])

    spacer(0.3)
    hr()
    elements.append(Paragraph(
        f"Prepared for {APPLICANT['full_name']}  |  "
        f"Application {APP['number']}  |  {TODAY}",
        S["Small"],
    ))

    # Build PDF
    doc.build(elements)
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    build()

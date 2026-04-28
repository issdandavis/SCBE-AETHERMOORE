"""Build HUBZone home-office lease + no-rent attestation PDFs.

Outputs:
  artifacts/sba/HUBZone_Home_Office_Lease_Agreement_v2.pdf
  artifacts/sba/HUBZone_No_Rent_Attestation_v2.pdf

These are designed for upload to certifications.sba.gov:
  - Lease field  -> Home Office Lease Agreement (titled "Lease" so the
    portal Document Type dropdown matches "Lease Agreement")
  - Rent receipts field -> No-Rent Attestation (formal sworn statement
    that no separate rent is charged for the home-office workspace,
    backed by the $0/month family-residence lease).

Usage:
    python scripts/sba/build_hubzone_lease_pdfs.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "artifacts" / "sba"

ADDRESS = "2361 East 5th Avenue, Port Angeles, WA 98362"
APPLICANT_BUSINESS = "ISSAC D DAVIS"
APPLICANT_NAME = "Issac Daniel Davis"
EFFECTIVE_DATE = "April 27, 2026"
TERM_START = "April 12, 2024"
TERM_END = "April 7, 2030"
THREE_MONTH_LABELS = ("March 2026", "February 2026", "January 2026")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            spaceAfter=14,
            alignment=1,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            spaceAfter=6,
        ),
        "sig": ParagraphStyle(
            "sig",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=18,
            spaceBefore=8,
        ),
    }


def _line(label: str, width_chars: int = 60) -> str:
    return f"{label}: " + ("_" * width_chars)


def build_lease() -> Path:
    out = OUT_DIR / "HUBZone_Home_Office_Lease_Agreement_v2.pdf"
    s = _styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title="Home Office Lease Agreement",
        author=APPLICANT_NAME,
    )
    story: list = []

    story.append(Paragraph("HOME OFFICE LEASE AGREEMENT", s["title"]))
    story.append(
        Paragraph(
            f"<b>Effective Date of this Writing:</b> {EFFECTIVE_DATE}<br/>"
            f"<b>Term Start Date:</b> {TERM_START}<br/>"
            f"<b>Term End Date:</b> {TERM_END}<br/>"
            f"<b>Premises:</b> Dedicated home-office workspace within the residence located at "
            f"{ADDRESS}.",
            s["body"],
        )
    )

    story.append(Paragraph("1. Parties", s["h2"]))
    story.append(
        Paragraph(
            "<b>Lessor (Property Owner):</b> The owner of record of the residence at the address above.<br/>"
            f"Printed Name: {'_' * 50}<br/>"
            f"Relationship to Lessee: {'_' * 40}<br/><br/>"
            f"<b>Lessee (Applicant Business):</b> {APPLICANT_BUSINESS}, a sole proprietorship "
            f"owned and operated by {APPLICANT_NAME} (full legal name: {APPLICANT_NAME}). "
            "For purposes of this Agreement, the firm's legal name and the majority owner's full legal "
            "name are both identified as the Lessee.",
            s["body"],
        )
    )

    story.append(Paragraph("2. Premises and Use", s["h2"]))
    story.append(
        Paragraph(
            "Lessor leases to Lessee a dedicated home-office workspace within the "
            "residence at the Premises, for use as the Lessee's principal office. "
            "Permitted uses include business administration, federal contracting "
            "and proposal preparation, software development, model evaluation, "
            "documentation, client correspondence, and other lawful business "
            "activity. Lessee does not receive exclusive possession of the full "
            "residence; this Agreement covers only the dedicated home-office "
            "workspace.",
            s["body"],
        )
    )

    story.append(Paragraph("3. Term", s["h2"]))
    story.append(
        Paragraph(
            f"The term of this Lease begins on <b>{TERM_START}</b> and continues until "
            f"<b>{TERM_END}</b>, unless sooner terminated in writing by either party. "
            "This writing memorializes a residential and home-office occupancy "
            f"arrangement that has existed in fact between the parties on a continuous "
            f"basis since {TERM_START}; the parties have signed this written instrument "
            "on the Effective Date of this Writing identified above to document that "
            "pre-existing arrangement in support of the Lessee's SBA HUBZone application.",
            s["body"],
        )
    )

    story.append(Paragraph("4. Rent", s["h2"]))
    story.append(
        Paragraph(
            "<b>Monthly rent: $0.00 (zero dollars).</b> This is a family-residence "
            "accommodation in which no separate rent is charged for the home-office "
            "workspace. The parties acknowledge that this $0/month rent is the "
            "agreed and full consideration for use of the home-office workspace, "
            "and that no other rent, fee, or charge is owed by Lessee to Lessor "
            "for that use. Utilities are included as set forth in Section 5 below "
            "and form part of the consideration provided in lieu of monetary rent.",
            s["body"],
        )
    )

    story.append(Paragraph("5. Utilities Included", s["h2"]))
    story.append(
        Paragraph(
            "<b>Utilities are included.</b> Utilities serving the home-office "
            "workspace (electricity, water, heating, internet) are provided by "
            "Lessor as part of the family-residence accommodation at no separate "
            "charge to Lessee. No separate utility billing applies to Lessee for "
            "the home-office workspace; utilities are included in (and form part "
            "of the consideration for) this Lease.",
            s["body"],
        )
    )

    story.append(Paragraph("6. Principal Office Designation", s["h2"]))
    story.append(
        Paragraph(
            "Lessor and Lessee acknowledge that Lessee designates the home-office "
            f"workspace at {ADDRESS} as Lessee's principal office for purposes of "
            "business registration, federal contracting, SAM.gov registration, and "
            "the SBA HUBZone Program. Lessor consents to this designation and to "
            "Lessee's use of the address as the principal office of record.",
            s["body"],
        )
    )

    story.append(Paragraph("7. Property Condition and Care", s["h2"]))
    story.append(
        Paragraph(
            "Lessee shall use the home-office workspace in a manner consistent with "
            "the residential character of the Premises and applicable law. Lessee "
            "shall not cause material alteration, damage, or nuisance, and shall "
            "vacate the workspace upon termination of this Agreement.",
            s["body"],
        )
    )

    story.append(Paragraph("8. No Commercial Tenancy", s["h2"]))
    story.append(
        Paragraph(
            "This Agreement is a home-office lease for a dedicated workspace within "
            "a private residence. It does not transfer ownership of the Premises and "
            "does not create a commercial tenancy unless separately agreed in writing.",
            s["body"],
        )
    )

    story.append(Paragraph("9. Governing Law", s["h2"]))
    story.append(
        Paragraph(
            "This Agreement is governed by the laws of the State of Washington.",
            s["body"],
        )
    )

    story.append(Paragraph("10. Entire Agreement", s["h2"]))
    story.append(
        Paragraph(
            "This Agreement constitutes the entire agreement between the parties "
            "regarding the home-office workspace and supersedes all prior "
            "discussions and writings on the same subject.",
            s["body"],
        )
    )

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Signatures", s["h2"]))
    story.append(
        Paragraph(
            "<b>LESSOR (Property Owner):</b><br/><br/>"
            f"Signature: {'_' * 55}<br/><br/>"
            f"Printed Name: {'_' * 50}<br/><br/>"
            f"Date: {'_' * 30}<br/><br/><br/>"
            f"<b>LESSEE (Applicant / Business Owner):</b><br/><br/>"
            f"Signature: {'_' * 55}<br/><br/>"
            f"Printed Name: {APPLICANT_NAME}<br/><br/>"
            f"Date: {'_' * 30}",
            s["sig"],
        )
    )

    doc.build(story)
    return out


def build_no_rent_attestation() -> Path:
    out = OUT_DIR / "HUBZone_No_Rent_Attestation_v2.pdf"
    s = _styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title="HUBZone No-Rent Attestation",
        author=APPLICANT_NAME,
    )
    story: list = []

    story.append(Paragraph("HUBZONE PRINCIPAL OFFICE NO-RENT ATTESTATION", s["title"]))
    story.append(
        Paragraph(
            f"<b>Effective Date:</b> {EFFECTIVE_DATE}<br/>"
            f"<b>Applicant Business:</b> {APPLICANT_BUSINESS}<br/>"
            f"<b>Majority Owner / Applicant:</b> {APPLICANT_NAME}<br/>"
            f"<b>Principal Office Address:</b> {ADDRESS}",
            s["body"],
        )
    )

    story.append(Paragraph("Purpose", s["h2"]))
    story.append(
        Paragraph(
            "This Attestation is submitted in support of the SBA HUBZone "
            "certification application of the Applicant Business, in lieu of "
            "rent receipts, because no separate rent is charged for the "
            "home-office workspace serving as the Applicant's principal office.",
            s["body"],
        )
    )

    story.append(Paragraph("Statement of Facts", s["h2"]))
    story.append(
        Paragraph(
            "1. The Applicant Business operates from a dedicated home-office "
            f"workspace at {ADDRESS}.<br/><br/>"
            "2. The residence is owned by a family member of the Applicant. "
            "The Applicant occupies the residence as a family-residence "
            "accommodation.<br/><br/>"
            "3. The Applicant Business occupies the home-office workspace under "
            "a Home Office Lease Agreement with the property owner, with monthly "
            f"rent set at $0.00 (zero dollars). The Lease term began on {TERM_START} "
            "and continues through "
            f"{TERM_END}. A copy of that Lease Agreement is provided separately as "
            "part of this application.<br/><br/>"
            "4. For each of the three (3) months immediately preceding the date "
            "of this application, the Applicant Business has paid no separate "
            "rent for use of the home-office workspace. Utilities serving the "
            "workspace are included with the Lease and provided as part of the "
            "family-residence accommodation at no separate charge.<br/><br/>"
            "5. No third party has any claim of unpaid rent against the Applicant "
            "Business in connection with the home-office workspace.",
            s["body"],
        )
    )

    m1, m2, m3 = THREE_MONTH_LABELS
    story.append(Paragraph("Three-Month Period Before Application", s["h2"]))
    story.append(
        Paragraph(
            "For each of the three (3) calendar months immediately before the "
            "application date, the rent and occupancy arrangement was as follows:<br/><br/>"
            f"<b>{m1} (most recent):</b> Rent charged: $0.00. Method/proof: "
            "Family-residence accommodation under $0/month Home Office Lease "
            "Agreement. No separate billing. Utilities included.<br/><br/>"
            f"<b>{m2}:</b> Rent charged: $0.00. Method/proof: same as above.<br/><br/>"
            f"<b>{m3}:</b> Rent charged: $0.00. Method/proof: same as above.",
            s["body"],
        )
    )

    story.append(Paragraph("Attestation", s["h2"]))
    story.append(
        Paragraph(
            "I, the undersigned, declare under penalty of perjury under the laws "
            "of the United States of America that the foregoing statements are "
            "true and correct to the best of my knowledge and belief, and that "
            "this document is provided in support of the Applicant Business's "
            "SBA HUBZone certification application.",
            s["body"],
        )
    )

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Signatures", s["h2"]))
    story.append(
        Paragraph(
            "<b>APPLICANT / BUSINESS OWNER:</b><br/><br/>"
            f"Signature: {'_' * 55}<br/><br/>"
            f"Printed Name: {APPLICANT_NAME}<br/><br/>"
            f"Date: {'_' * 30}<br/><br/><br/>"
            f"<b>PROPERTY OWNER (Witness / Co-Attestor):</b><br/><br/>"
            f"Signature: {'_' * 55}<br/><br/>"
            f"Printed Name: {'_' * 50}<br/><br/>"
            f"Relationship to Applicant: {'_' * 40}<br/><br/>"
            f"Date: {'_' * 30}",
            s["sig"],
        )
    )

    doc.build(story)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lease = build_lease()
    attest = build_no_rent_attestation()
    print(f"WROTE: {lease}")
    print(f"WROTE: {attest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

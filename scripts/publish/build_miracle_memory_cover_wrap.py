"""Build the KDP paperback cover wrap PDF for The Miracle Was The Memory.

Output:
    artifacts/book/kdp/miracle-memory/miracle-memory-cover-wrap.pdf

Trim 5.5 x 8.5 in, cream paper, B&W interior, 468 pages.
Spine width (KDP cream B&W formula): page_count * 0.0025 = 1.17 in.
Bleed: 0.125 in on all four outer edges.
Wrap dimensions: 12.42 x 8.75 in.

This is a clean literary cover. Cream ground, serif typography, small lamp
glyph centered above the title on the front, back-cover copy from
cover-copy.md, spine with title-author-lamp.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "book" / "kdp" / "miracle-memory"
OUT_PDF = OUT_DIR / "miracle-memory-cover-wrap.pdf"


PAGE_COUNT = 468
SPINE_PER_PAGE_IN = 0.0025  # KDP cream B&W formula
TRIM_W = 5.5
TRIM_H = 8.5
BLEED = 0.125
SAFE = 0.25
SPINE_W = PAGE_COUNT * SPINE_PER_PAGE_IN  # 1.17 in

WRAP_W = BLEED + TRIM_W + SPINE_W + TRIM_W + BLEED  # 12.42 in
WRAP_H = BLEED + TRIM_H + BLEED  # 8.75 in

# Section x-anchors in inches (left to right across the wrap)
BACK_LEFT = BLEED
BACK_RIGHT = BACK_LEFT + TRIM_W
SPINE_LEFT = BACK_RIGHT
SPINE_RIGHT = SPINE_LEFT + SPINE_W
FRONT_LEFT = SPINE_RIGHT
FRONT_RIGHT = FRONT_LEFT + TRIM_W

# Colors (literary cream / dark ink palette)
CREAM = HexColor("#F2E8D5")
INK = HexColor("#1C1A16")
INK_SOFT = HexColor("#3A342B")
RULE = HexColor("#6B5E48")


def register_fonts() -> tuple[str, str, str]:
    """Try to register Georgia (matches interior). Fall back to Times."""
    georgia_dir = Path("C:/Windows/Fonts")
    try:
        pdfmetrics.registerFont(TTFont("Georgia", str(georgia_dir / "georgia.ttf")))
        pdfmetrics.registerFont(TTFont("Georgia-Bold", str(georgia_dir / "georgiab.ttf")))
        pdfmetrics.registerFont(TTFont("Georgia-Italic", str(georgia_dir / "georgiai.ttf")))
        return "Georgia", "Georgia-Bold", "Georgia-Italic"
    except Exception:
        return "Times-Roman", "Times-Bold", "Times-Italic"


def draw_background(c: canvas.Canvas) -> None:
    c.setFillColor(CREAM)
    c.rect(0, 0, WRAP_W * inch, WRAP_H * inch, fill=1, stroke=0)


def draw_lamp_glyph(c: canvas.Canvas, cx_in: float, cy_in: float, size_in: float, color=INK_SOFT) -> None:
    """A small classical oil-lamp silhouette, centered at (cx, cy)."""
    cx = cx_in * inch
    cy = cy_in * inch
    s = size_in * inch

    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(0.4)

    # Body: elongated oval (the reservoir)
    body_w = s * 1.6
    body_h = s * 0.55
    c.ellipse(cx - body_w / 2, cy - body_h / 2, cx + body_w / 2, cy + body_h / 2, fill=1, stroke=0)

    # Spout: small triangle on the right
    sp = [
        (cx + body_w / 2 - s * 0.05, cy + body_h * 0.15),
        (cx + body_w / 2 + s * 0.45, cy + body_h * 0.05),
        (cx + body_w / 2 - s * 0.05, cy - body_h * 0.15),
    ]
    p = c.beginPath()
    p.moveTo(*sp[0])
    p.lineTo(*sp[1])
    p.lineTo(*sp[2])
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Handle: small loop on the left
    handle_cx = cx - body_w / 2 + s * 0.05
    handle_cy = cy
    c.setLineWidth(s * 0.08)
    c.setStrokeColor(color)
    c.arc(
        handle_cx - s * 0.28,
        handle_cy - s * 0.28,
        handle_cx + s * 0.28,
        handle_cy + s * 0.28,
        startAng=200,
        extent=120,
    )

    # Flame: small teardrop above the spout
    flame_cx = cx + body_w / 2 + s * 0.25
    flame_cy = cy + body_h * 0.6
    c.setFillColor(color)
    c.setStrokeColor(color)
    p2 = c.beginPath()
    p2.moveTo(flame_cx, flame_cy - s * 0.05)
    p2.curveTo(
        flame_cx + s * 0.2, flame_cy + s * 0.1,
        flame_cx + s * 0.05, flame_cy + s * 0.35,
        flame_cx, flame_cy + s * 0.42,
    )
    p2.curveTo(
        flame_cx - s * 0.1, flame_cy + s * 0.32,
        flame_cx - s * 0.15, flame_cy + s * 0.1,
        flame_cx, flame_cy - s * 0.05,
    )
    p2.close()
    c.drawPath(p2, fill=1, stroke=0)


def draw_centered_string(
    c: canvas.Canvas,
    text: str,
    x_in: float,
    y_in: float,
    font: str,
    size_pt: float,
    color=INK,
    char_space: float = 0.0,
) -> None:
    if char_space and char_space > 0:
        t = c.beginText()
        t.setFont(font, size_pt)
        t.setFillColor(color)
        t.setCharSpace(char_space)
        width = pdfmetrics.stringWidth(text, font, size_pt) + char_space * max(len(text) - 1, 0)
        t.setTextOrigin(x_in * inch - width / 2, y_in * inch)
        t.textOut(text)
        c.drawText(t)
    else:
        c.setFont(font, size_pt)
        c.setFillColor(color)
        c.drawCentredString(x_in * inch, y_in * inch, text)


def draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x_in: float,
    y_top_in: float,
    width_in: float,
    font: str,
    size_pt: float,
    leading_pt: float,
    color=INK,
    align: str = "left",
) -> float:
    """Manual word-wrap and draw. Returns the y-coordinate after the last line (in inches)."""
    c.setFont(font, size_pt)
    c.setFillColor(color)
    words = text.split()
    if not words:
        return y_top_in
    lines: list[str] = []
    current: list[str] = []
    max_w = width_in * inch
    for w in words:
        trial = " ".join(current + [w])
        if pdfmetrics.stringWidth(trial, font, size_pt) <= max_w or not current:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))

    y_pt = y_top_in * inch
    leading = leading_pt
    for line in lines:
        if align == "left":
            c.drawString(x_in * inch, y_pt - leading, line)
        elif align == "center":
            c.drawCentredString((x_in + width_in / 2) * inch, y_pt - leading, line)
        else:
            c.drawRightString((x_in + width_in) * inch, y_pt - leading, line)
        y_pt -= leading
    return y_pt / inch


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def draw_front_cover(c: canvas.Canvas, regular: str, bold: str, italic: str) -> None:
    center_x = FRONT_LEFT + TRIM_W / 2

    # Decorative horizontal rules at top and bottom of front
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    top_rule_y = WRAP_H - BLEED - SAFE - 0.05
    bot_rule_y = BLEED + SAFE + 0.05
    c.line((FRONT_LEFT + SAFE) * inch, top_rule_y * inch, (FRONT_RIGHT - SAFE) * inch, top_rule_y * inch)
    c.line((FRONT_LEFT + SAFE) * inch, bot_rule_y * inch, (FRONT_RIGHT - SAFE) * inch, bot_rule_y * inch)

    # Tagline at top, small caps style
    draw_centered_string(
        c,
        "A WORK OF CREATIVE NONFICTION",
        center_x,
        top_rule_y - 0.30,
        regular,
        8.5,
        color=INK_SOFT,
        char_space=1.4,
    )

    # Lamp glyph above the title
    draw_lamp_glyph(c, center_x, WRAP_H - BLEED - 2.05, 0.55, color=INK_SOFT)

    # Title — two lines, centered, large
    draw_centered_string(c, "THE MIRACLE", center_x, WRAP_H - BLEED - 3.20, bold, 34.0, color=INK, char_space=1.2)
    draw_centered_string(c, "WAS THE MEMORY", center_x, WRAP_H - BLEED - 3.80, bold, 34.0, color=INK, char_space=1.2)

    # Small ornamental rule between title and subtitle
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    rule_y = (WRAP_H - BLEED - 4.30) * inch
    c.line((center_x - 0.7) * inch, rule_y, (center_x + 0.7) * inch, rule_y)

    # Subtitle — italic, wrapped
    subtitle = "A Human Reading of Jesus, Empire,\nand the Stories That Would Not Die"
    sub_lines = subtitle.split("\n")
    y = WRAP_H - BLEED - 4.55
    for line in sub_lines:
        draw_centered_string(c, line, center_x, y, italic, 13.0, color=INK_SOFT)
        y -= 0.24

    # Epigraph attribution — Mara bar Serapion (small)
    draw_centered_string(
        c,
        "Nor did the wise King die for good;",
        center_x,
        WRAP_H - BLEED - 6.20,
        italic,
        10.5,
        color=INK_SOFT,
    )
    draw_centered_string(
        c,
        "he lived on in the teaching which he had given.",
        center_x,
        WRAP_H - BLEED - 6.42,
        italic,
        10.5,
        color=INK_SOFT,
    )
    draw_centered_string(
        c,
        "— MARA BAR SERAPION, c. 73 CE",
        center_x,
        WRAP_H - BLEED - 6.75,
        regular,
        8.0,
        color=INK_SOFT,
        char_space=1.0,
    )

    # Author byline — bottom
    draw_centered_string(
        c,
        "ISSAC DANIEL DAVIS",
        center_x,
        bot_rule_y + 0.40,
        bold,
        14.0,
        color=INK,
        char_space=2.4,
    )


def draw_back_cover(c: canvas.Canvas, regular: str, bold: str, italic: str) -> None:
    # Hook at top
    hook_y = WRAP_H - BLEED - SAFE - 0.55
    draw_centered_string(
        c,
        "Rome had the nails. We had the memory.",
        BACK_LEFT + TRIM_W / 2,
        hook_y,
        italic,
        14.0,
        color=INK,
    )

    # Small rule under the hook
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    rule_y = (hook_y - 0.20) * inch
    c.line(
        (BACK_LEFT + TRIM_W / 2 - 0.9) * inch,
        rule_y,
        (BACK_LEFT + TRIM_W / 2 + 0.9) * inch,
        rule_y,
    )

    # Three body paragraphs (left-aligned, narrower column)
    col_left = BACK_LEFT + 0.65
    col_width = TRIM_W - 1.30

    paragraphs = [
        (
            "Dagan is a road thief in Galilee in the years after Herod died. "
            "He has watched a city burn for one bad raid, buried his only "
            "friend in the wrong dirt, and learned the lower-city rule about "
            "mercy: mercy is what gets you killed when the patrol asks who "
            "you were drinking with."
        ),
        (
            "Then a Galilean carpenter starts turning up in the same rooms. "
            "He does not preach at Dagan. He hands him water. He gives him "
            "bread. He pulls a woman out of a stoning and lets her walk. He "
            "gets killed under Roman procedure on a Friday morning. Dagan "
            "does not believe any of it. He keeps showing up anyway."
        ),
        (
            "Sixty years later, Dagan is eighty-three and dictating to his "
            "twelve-year-old grandson. The Temple has fallen. The "
            "eyewitnesses are dying. The first writers are at work. "
            "The Miracle Was the Memory follows the witnesses across the "
            "lifetime they spent carrying a story that had no historical "
            "right to survive. Cold records and warm rooms. Lamps that "
            "would not stop burning."
        ),
    ]

    y = hook_y - 0.55
    for para in paragraphs:
        y = draw_wrapped(c, para, col_left, y, col_width, regular, 10.0, 13.5, color=INK)
        y -= 0.15  # paragraph gap

    # Author bio — positioned above the barcode strip, full column width
    bio_top = BLEED + SAFE + 1.65
    bio_text = (
        "Issac Daniel Davis is a writer in Port Angeles, Washington, at the "
        "northern edge of the Olympic Peninsula. The Miracle Was the Memory "
        "is his first book."
    )
    draw_wrapped(c, bio_text, col_left, bio_top, col_width, italic, 9.5, 12.5, color=INK_SOFT, align="center")

    # Bottom-left line — above the barcode row to avoid overlap
    draw_centered_string(
        c,
        "A WORK OF CREATIVE NONFICTION",
        BACK_LEFT + SAFE + 1.40,
        BLEED + SAFE + 0.55,
        regular,
        8.0,
        color=INK_SOFT,
        char_space=1.6,
    )

    # Bottom-right barcode placeholder (KDP will overprint actual barcode)
    bc_w = 1.85
    bc_h = 1.00
    bc_x_in = BACK_RIGHT - SAFE - bc_w
    bc_y_in = BLEED + SAFE + 0.10
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(INK_SOFT)
    c.setLineWidth(0.4)
    c.rect(bc_x_in * inch, bc_y_in * inch, bc_w * inch, bc_h * inch, fill=1, stroke=1)
    c.setFillColor(INK_SOFT)
    c.setFont(regular, 6.5)
    c.drawCentredString(
        (bc_x_in + bc_w / 2) * inch,
        (bc_y_in + bc_h / 2) * inch,
        "KDP BARCODE AREA",
    )


def draw_spine(c: canvas.Canvas, regular: str, bold: str, italic: str) -> None:
    cx = SPINE_LEFT + SPINE_W / 2

    # Rotate text 90 degrees CCW for spine
    c.saveState()
    c.translate(cx * inch, (WRAP_H / 2) * inch)
    c.rotate(90)

    # Title on the top half (rotated)
    title = "THE MIRACLE WAS THE MEMORY"
    t = c.beginText()
    t.setFont(bold, 16.0)
    t.setFillColor(INK)
    t.setCharSpace(1.6)
    w = pdfmetrics.stringWidth(title, bold, 16.0) + 1.6 * (len(title) - 1)
    t.setTextOrigin(1.55 * inch - w / 2, 0.07 * inch)
    t.textOut(title)
    c.drawText(t)

    # Author at the lower half
    author = "ISSAC DANIEL DAVIS"
    t2 = c.beginText()
    t2.setFont(regular, 11.0)
    t2.setFillColor(INK_SOFT)
    t2.setCharSpace(2.0)
    w2 = pdfmetrics.stringWidth(author, regular, 11.0) + 2.0 * (len(author) - 1)
    t2.setTextOrigin(-2.6 * inch - w2 / 2, 0.07 * inch)
    t2.textOut(author)
    c.drawText(t2)

    c.restoreState()

    # Lamp glyph removed from spine — title + author already balance the narrow 1.17" column.


def draw_safe_area_guides(c: canvas.Canvas) -> None:
    """Optional: faint guides for the trim and bleed lines. Comment out for final."""
    return  # disabled in production output


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PDF), pagesize=(WRAP_W * inch, WRAP_H * inch))
    c.setTitle("The Miracle Was The Memory — Cover Wrap")
    c.setAuthor("Issac Daniel Davis")
    c.setSubject("KDP cover wrap, 5.5x8.5, 468pp, cream interior")

    regular, bold, italic = register_fonts()
    draw_background(c)
    draw_back_cover(c, regular, bold, italic)
    draw_spine(c, regular, bold, italic)
    draw_front_cover(c, regular, bold, italic)
    draw_safe_area_guides(c)

    c.showPage()
    c.save()

    print(f"wrote {OUT_PDF}")
    print(f"  wrap: {WRAP_W:.3f} x {WRAP_H:.3f} in")
    print(f"  spine: {SPINE_W:.3f} in ({PAGE_COUNT} pages @ {SPINE_PER_PAGE_IN} in/page)")


if __name__ == "__main__":
    build()

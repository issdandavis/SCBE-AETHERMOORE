"""Cover-wrap PDF generator with KDP-correct spine math.

Generates the full wrap (back + spine + front, with bleed) sized for the
binding the profile specifies. Trim, spine, and bleed are derived from the
profile so this works for any KDP-supported trim size and page count.

The visual treatment is the bookforge default: cream ground, serif typography,
small lamp glyph on the front, hook + body + bio + barcode placeholder on
the back. Replace `draw_front_cover` / `draw_back_cover` with your own
callables to ship a different visual.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .profile import Profile


BLEED_IN = 0.125
SAFE_IN = 0.25

CREAM = HexColor("#F2E8D5")
INK = HexColor("#1C1A16")
INK_SOFT = HexColor("#3A342B")
RULE = HexColor("#6B5E48")


def _register_font(body_font: str) -> tuple[str, str, str]:
    win = Path("C:/Windows/Fonts")
    candidates = {
        "Georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf"),
        "Times New Roman": ("times.ttf", "timesbd.ttf", "timesi.ttf"),
    }
    files = candidates.get(body_font)
    if not files:
        return "Times-Roman", "Times-Bold", "Times-Italic"
    try:
        pdfmetrics.registerFont(TTFont(body_font, str(win / files[0])))
        pdfmetrics.registerFont(TTFont(f"{body_font}-Bold", str(win / files[1])))
        pdfmetrics.registerFont(TTFont(f"{body_font}-Italic", str(win / files[2])))
        return body_font, f"{body_font}-Bold", f"{body_font}-Italic"
    except Exception:
        return "Times-Roman", "Times-Bold", "Times-Italic"


def _spaced_centered(c, text, cx_in, y_in, font, size_pt, color, char_space=0.0):
    if char_space and char_space > 0:
        t = c.beginText()
        t.setFont(font, size_pt)
        t.setFillColor(color)
        t.setCharSpace(char_space)
        w = pdfmetrics.stringWidth(text, font, size_pt) + char_space * max(len(text) - 1, 0)
        t.setTextOrigin(cx_in * inch - w / 2, y_in * inch)
        t.textOut(text)
        c.drawText(t)
    else:
        c.setFont(font, size_pt)
        c.setFillColor(color)
        c.drawCentredString(cx_in * inch, y_in * inch, text)


def _wrap_text(c, text, x_in, y_top_in, width_in, font, size_pt, leading_pt, color, align="left"):
    c.setFont(font, size_pt)
    c.setFillColor(color)
    words = text.split()
    if not words:
        return y_top_in
    lines, current = [], []
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
    for line in lines:
        if align == "left":
            c.drawString(x_in * inch, y_pt - leading_pt, line)
        elif align == "center":
            c.drawCentredString((x_in + width_in / 2) * inch, y_pt - leading_pt, line)
        else:
            c.drawRightString((x_in + width_in) * inch, y_pt - leading_pt, line)
        y_pt -= leading_pt
    return y_pt / inch


def _draw_lamp(c, cx_in, cy_in, size_in, color=INK_SOFT):
    cx, cy, s = cx_in * inch, cy_in * inch, size_in * inch
    c.setFillColor(color)
    c.setStrokeColor(color)
    bw, bh = s * 1.6, s * 0.55
    c.ellipse(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, fill=1, stroke=0)
    p = c.beginPath()
    p.moveTo(cx + bw / 2 - s * 0.05, cy + bh * 0.15)
    p.lineTo(cx + bw / 2 + s * 0.45, cy + bh * 0.05)
    p.lineTo(cx + bw / 2 - s * 0.05, cy - bh * 0.15)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setLineWidth(s * 0.08)
    c.arc(cx - bw / 2 + s * 0.05 - s * 0.28, cy - s * 0.28,
          cx - bw / 2 + s * 0.05 + s * 0.28, cy + s * 0.28,
          startAng=200, extent=120)
    flame_cx, flame_cy = cx + bw / 2 + s * 0.25, cy + bh * 0.6
    p2 = c.beginPath()
    p2.moveTo(flame_cx, flame_cy - s * 0.05)
    p2.curveTo(flame_cx + s * 0.2, flame_cy + s * 0.1, flame_cx + s * 0.05, flame_cy + s * 0.35,
               flame_cx, flame_cy + s * 0.42)
    p2.curveTo(flame_cx - s * 0.1, flame_cy + s * 0.32, flame_cx - s * 0.15, flame_cy + s * 0.1,
               flame_cx, flame_cy - s * 0.05)
    p2.close()
    c.drawPath(p2, fill=1, stroke=0)


def build(
    profile: Profile,
    *,
    out_pdf: Optional[Path] = None,
    hook: str = "",
    blurb_paragraphs: Optional[list[str]] = None,
    author_bio: str = "",
    bottom_left_caption: str = "",
) -> Path:
    """Build the cover wrap PDF for the binding in `profile`."""
    p = profile
    if p.page_count is None:
        raise ValueError("profile.page_count must be set before building the cover wrap")
    spine_w = p.spine_width_in()

    wrap_w = BLEED_IN + p.trim_w_in + spine_w + p.trim_w_in + BLEED_IN
    wrap_h = BLEED_IN + p.trim_h_in + BLEED_IN

    back_left = BLEED_IN
    back_right = back_left + p.trim_w_in
    spine_left = back_right
    spine_right = spine_left + spine_w
    front_left = spine_right
    front_right = front_left + p.trim_w_in

    p.output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_pdf or (p.output_dir / f"{p.source_md.stem}-cover-wrap.pdf")
    out_pdf = Path(out_pdf).resolve()

    regular, bold, italic = _register_font(p.body_font)
    c = canvas.Canvas(str(out_pdf), pagesize=(wrap_w * inch, wrap_h * inch))
    c.setTitle(f"{p.title} — Cover Wrap")
    c.setAuthor(p.author)

    # Background
    c.setFillColor(CREAM)
    c.rect(0, 0, wrap_w * inch, wrap_h * inch, fill=1, stroke=0)

    # ---- Back cover ----
    if hook:
        hook_y = wrap_h - BLEED_IN - SAFE_IN - 0.55
        _spaced_centered(c, hook, back_left + p.trim_w_in / 2, hook_y, italic, 14.0, INK)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        ry = (hook_y - 0.20) * inch
        c.line((back_left + p.trim_w_in / 2 - 0.9) * inch, ry,
               (back_left + p.trim_w_in / 2 + 0.9) * inch, ry)
        y = hook_y - 0.55
    else:
        y = wrap_h - BLEED_IN - SAFE_IN - 0.55

    col_left = back_left + 0.65
    col_width = p.trim_w_in - 1.30

    for para in (blurb_paragraphs or []):
        y = _wrap_text(c, para, col_left, y, col_width, regular, 10.0, 13.5, INK)
        y -= 0.15

    if author_bio:
        bio_top = BLEED_IN + SAFE_IN + 1.65
        _wrap_text(c, author_bio, col_left, bio_top, col_width, italic, 9.5, 12.5, INK_SOFT, align="center")

    if bottom_left_caption:
        _spaced_centered(c, bottom_left_caption, back_left + SAFE_IN + 1.40,
                         BLEED_IN + SAFE_IN + 0.55, regular, 8.0, INK_SOFT, char_space=1.6)

    bc_w, bc_h = 1.85, 1.00
    bc_x = back_right - SAFE_IN - bc_w
    bc_y = BLEED_IN + SAFE_IN + 0.10
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(INK_SOFT)
    c.setLineWidth(0.4)
    c.rect(bc_x * inch, bc_y * inch, bc_w * inch, bc_h * inch, fill=1, stroke=1)
    c.setFillColor(INK_SOFT)
    c.setFont(regular, 6.5)
    c.drawCentredString((bc_x + bc_w / 2) * inch, (bc_y + bc_h / 2) * inch, "KDP BARCODE AREA")

    # ---- Spine ----
    cx_spine = spine_left + spine_w / 2
    c.saveState()
    c.translate(cx_spine * inch, (wrap_h / 2) * inch)
    c.rotate(90)
    title_text = p.title.upper()
    t = c.beginText()
    t.setFont(bold, 16.0)
    t.setFillColor(INK)
    t.setCharSpace(1.6)
    tw = pdfmetrics.stringWidth(title_text, bold, 16.0) + 1.6 * (len(title_text) - 1)
    t.setTextOrigin(1.55 * inch - tw / 2, 0.07 * inch)
    t.textOut(title_text)
    c.drawText(t)
    if p.author:
        author_text = p.author.upper()
        t2 = c.beginText()
        t2.setFont(regular, 11.0)
        t2.setFillColor(INK_SOFT)
        t2.setCharSpace(2.0)
        aw = pdfmetrics.stringWidth(author_text, regular, 11.0) + 2.0 * (len(author_text) - 1)
        t2.setTextOrigin(-2.6 * inch - aw / 2, 0.07 * inch)
        t2.textOut(author_text)
        c.drawText(t2)
    c.restoreState()

    # ---- Front cover ----
    center_x = front_left + p.trim_w_in / 2
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    top_rule_y = wrap_h - BLEED_IN - SAFE_IN - 0.05
    bot_rule_y = BLEED_IN + SAFE_IN + 0.05
    c.line((front_left + SAFE_IN) * inch, top_rule_y * inch,
           (front_right - SAFE_IN) * inch, top_rule_y * inch)
    c.line((front_left + SAFE_IN) * inch, bot_rule_y * inch,
           (front_right - SAFE_IN) * inch, bot_rule_y * inch)

    if bottom_left_caption:
        _spaced_centered(c, bottom_left_caption, center_x, top_rule_y - 0.30,
                         regular, 8.5, INK_SOFT, char_space=1.4)

    _draw_lamp(c, center_x, wrap_h - BLEED_IN - 2.05, 0.55, color=INK_SOFT)

    title_words = p.title.split()
    if len(title_words) >= 4:
        half = len(title_words) // 2
        line1 = " ".join(title_words[:half]).upper()
        line2 = " ".join(title_words[half:]).upper()
        _spaced_centered(c, line1, center_x, wrap_h - BLEED_IN - 3.20, bold, 34.0, INK, char_space=1.2)
        _spaced_centered(c, line2, center_x, wrap_h - BLEED_IN - 3.80, bold, 34.0, INK, char_space=1.2)
    else:
        _spaced_centered(c, p.title.upper(), center_x, wrap_h - BLEED_IN - 3.50, bold, 34.0, INK, char_space=1.2)

    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    rule_y = (wrap_h - BLEED_IN - 4.30) * inch
    c.line((center_x - 0.7) * inch, rule_y, (center_x + 0.7) * inch, rule_y)

    if p.subtitle:
        sub_lines = [p.subtitle]
        if len(p.subtitle) > 45:
            words = p.subtitle.split()
            half = len(words) // 2
            sub_lines = [" ".join(words[:half]), " ".join(words[half:])]
        y_sub = wrap_h - BLEED_IN - 4.55
        for line in sub_lines:
            _spaced_centered(c, line, center_x, y_sub, italic, 13.0, INK_SOFT)
            y_sub -= 0.24

    if p.epigraph_enabled and p.epigraph_text:
        ep_lines = p.epigraph_text.split(". ")
        if len(ep_lines) == 1 and ";" in p.epigraph_text:
            ep_lines = p.epigraph_text.split("; ")
            ep_lines = [ep_lines[0] + ";", ep_lines[1]]
        elif len(ep_lines) > 1:
            ep_lines = [ep_lines[0] + ".", ". ".join(ep_lines[1:])]
        y_ep = wrap_h - BLEED_IN - 6.20
        for line in ep_lines:
            _spaced_centered(c, line, center_x, y_ep, italic, 10.5, INK_SOFT)
            y_ep -= 0.22
        if p.epigraph_attribution:
            _spaced_centered(c, f"— {p.epigraph_attribution.upper()}", center_x,
                             y_ep - 0.10, regular, 8.0, INK_SOFT, char_space=1.0)

    if p.author:
        _spaced_centered(c, p.author.upper(), center_x, bot_rule_y + 0.40,
                         bold, 14.0, INK, char_space=2.4)

    c.showPage()
    c.save()
    return out_pdf

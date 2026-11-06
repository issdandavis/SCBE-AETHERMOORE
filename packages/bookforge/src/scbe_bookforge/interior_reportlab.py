"""ReportLab interior PDF builder (XeLaTeX fallback).

Quality is lower than the XeLaTeX path (no real hyphenation, no microtype),
but it always works without a TeX install. Produces a print-clean PDF at the
profile's trim, margins, and typography.
"""

from __future__ import annotations

import html as html_module
import re
import textwrap
from pathlib import Path
from typing import Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch as rl_inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, XPreformatted


class _MirrorMarginDoc(BaseDocTemplate):
    """BaseDocTemplate that alternates recto/verso frames so the gutter is always inside."""

    def handle_pageBegin(self):
        # Pick the template for the page about to be rendered. ReportLab increments self.page at the start
        # of handle_pageBegin, so we set it BEFORE calling the parent (which uses the current pageTemplate).
        next_page = self.page + 1
        target_id = "recto" if next_page % 2 == 1 else "verso"
        for t in self.pageTemplates:
            if t.id == target_id:
                self.pageTemplate = t
                break
        BaseDocTemplate.handle_pageBegin(self)

from .manuscript import Block, clean_source_text, parse_markdown
from .profile import Profile


def _draw_page_ornament(c, doc, profile: Profile, page_w: float, page_h: float) -> None:
    """Draw a restrained, mirrored page ornament in the outside margin."""
    style = profile.ornament_style
    if style == "none":
        return
    color = colors.HexColor(profile.ornament_color)
    outer_right = doc.page % 2 == 1
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    if hasattr(c, "setStrokeAlpha"):
        c.setStrokeAlpha(profile.ornament_opacity)
    if hasattr(c, "setFillAlpha"):
        c.setFillAlpha(profile.ornament_opacity)

    if style == "gold_rule":
        inset = 0.22 * rl_inch
        c.setLineWidth(0.65)
        c.rect(inset, inset, page_w - 2 * inset, page_h - 2 * inset, fill=0, stroke=1)
    elif style == "water_channel":
        width = 1.05 * rl_inch
        height = 0.72 * rl_inch
        x0 = page_w - width if outer_right else 0
        y0 = 0.16 * rl_inch
        c.setLineWidth(0.6)
        for offset in (0.0, 0.12, 0.24, 0.36):
            path = c.beginPath()
            path.moveTo(x0, y0 + offset * rl_inch)
            path.curveTo(
                x0 + width * 0.28,
                y0 + height * 0.72 + offset * rl_inch,
                x0 + width * 0.62,
                y0 - height * 0.14 + offset * rl_inch,
                x0 + width,
                y0 + height * 0.48 + offset * rl_inch,
            )
            c.drawPath(path, fill=0, stroke=1)
    elif style == "rose":
        cx = page_w - 0.34 * rl_inch if outer_right else 0.34 * rl_inch
        cy = page_h - 0.38 * rl_inch
        petal = 0.09 * rl_inch
        for dx, dy in ((0, petal), (petal, 0), (0, -petal), (-petal, 0)):
            c.circle(cx + dx, cy + dy, petal * 0.72, fill=0, stroke=1)
        c.circle(cx, cy, petal * 0.5, fill=1, stroke=0)
        stem = c.beginPath()
        stem.moveTo(cx, cy - petal)
        stem.curveTo(cx - petal * 0.4, cy - petal * 2, cx + petal, cy - petal * 3.2, cx, cy - petal * 4.3)
        c.drawPath(stem, fill=0, stroke=1)
    c.restoreState()


def _register_font(profile: Profile) -> tuple[str, str, str]:
    name = profile.body_font
    candidates = {
        "Georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf"),
        "Times New Roman": ("times.ttf", "timesbd.ttf", "timesi.ttf"),
        "Cambria": ("cambria.ttc", "cambriab.ttf", "cambriai.ttf"),
        "Garamond": ("GARA.TTF", "GARABD.TTF", "GARAIT.TTF"),
    }
    files = candidates.get(name)
    if not files:
        return "Times-Roman", "Times-Bold", "Times-Italic"
    win = Path("C:/Windows/Fonts")
    try:
        pdfmetrics.registerFont(TTFont(name, str(win / files[0])))
        pdfmetrics.registerFont(TTFont(f"{name}-Bold", str(win / files[1])))
        pdfmetrics.registerFont(TTFont(f"{name}-Italic", str(win / files[2])))
        return name, f"{name}-Bold", f"{name}-Italic"
    except Exception:
        return "Times-Roman", "Times-Bold", "Times-Italic"


_INLINE_RE = re.compile(r"(`[^`]+`|\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*)")


def _md_inline(text: str) -> str:
    """Markdown inline to ReportLab Paragraph HTML."""
    pieces = []
    for part in _INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("***") and part.endswith("***"):
            pieces.append(f"<b><i>{html_module.escape(part[3:-3])}</i></b>")
        elif part.startswith("**") and part.endswith("**"):
            pieces.append(f"<b>{html_module.escape(part[2:-2])}</b>")
        elif part.startswith("*") and part.endswith("*"):
            pieces.append(f"<i>{html_module.escape(part[1:-1])}</i>")
        elif part.startswith("`") and part.endswith("`"):
            pieces.append(f'<font name="Courier">{html_module.escape(part[1:-1])}</font>')
        else:
            pieces.append(html_module.escape(part))
    return "".join(pieces)


def _wrap_code(text: str, width: int = 72) -> str:
    """Wrap long terminal/code lines without discarding indentation."""
    wrapped: list[str] = []
    for line in text.splitlines() or [""]:
        if not line:
            wrapped.append("")
            continue
        leading = line[: len(line) - len(line.lstrip())]
        parts = textwrap.wrap(
            line,
            width=width,
            subsequent_indent=leading + "    ",
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        wrapped.extend(parts or [line])
    return "\n".join(wrapped)


def _body_blocks(blocks: Iterable[Block], title: str) -> list[Block]:
    """Drop the top H1 title block; keep everything from the first H2 onward."""
    out: list[Block] = []
    started = False
    for b in blocks:
        if b.kind == "heading" and b.level == 2:
            started = True
        if started:
            out.append(b)
    if not out:
        return [b for b in blocks if not (b.kind == "heading" and b.level == 1 and b.text == title)]
    return out


def _contents_blocks(blocks: Iterable[Block]) -> list[Block]:
    contents: list[Block] = []
    for b in blocks:
        if b.kind != "heading":
            continue
        text = b.text.strip()
        lower = text.lower()
        if b.level == 1 and (lower.startswith("part ") or lower == "back matter"):
            contents.append(b)
        elif b.level == 2:
            contents.append(b)
    return contents


def build(profile: Profile, *, out_pdf: Optional[Path] = None) -> Path:
    p = profile
    p.output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_pdf or (p.output_dir / f"{p.source_md.stem}-interior.pdf")
    out_pdf = Path(out_pdf).resolve()

    regular, bold, italic = _register_font(p)
    source = p.source_md.read_text(encoding="utf-8")
    source, _ = clean_source_text(source)
    blocks = _body_blocks(parse_markdown(source), p.title)

    page_w = p.trim_w_in * rl_inch
    page_h = p.trim_h_in * rl_inch
    inside = p.effective_inside_in * rl_inch
    outside = p.outside_in * rl_inch
    top = p.top_in * rl_inch
    bottom = p.bottom_in * rl_inch
    frame_w = page_w - inside - outside
    frame_h = page_h - top - bottom

    # Recto (odd-page, right-hand): inside margin on the LEFT.
    recto_frame = Frame(inside, bottom, frame_w, frame_h, id="recto-frame",
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    # Verso (even-page, left-hand): inside margin on the RIGHT (so left margin = outside).
    verso_frame = Frame(outside, bottom, frame_w, frame_h, id="verso-frame",
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc = _MirrorMarginDoc(
        str(out_pdf),
        pagesize=(page_w, page_h),
        title=p.title,
        author=p.author,
        initialFontName=regular,
    )
    def draw_ornament(c, d):
        _draw_page_ornament(c, d, p, page_w, page_h)

    doc.addPageTemplates([
        PageTemplate(id="recto", frames=[recto_frame], onPage=draw_ornament),
        PageTemplate(id="verso", frames=[verso_frame], onPage=draw_ornament),
    ])

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName=regular, fontSize=p.body_size_pt, leading=p.leading_pt,
        firstLineIndent=p.first_line_indent_in * rl_inch,
        alignment=TA_JUSTIFY,
    )
    body_first = ParagraphStyle("BodyFirst", parent=body, firstLineIndent=0)
    chapter = ParagraphStyle(
        "Chapter", parent=styles["Heading1"],
        fontName=bold, fontSize=p.chapter_title_size_pt,
        leading=p.chapter_title_size_pt + 4, alignment=TA_CENTER,
        spaceBefore=0.55 * rl_inch, spaceAfter=0.25 * rl_inch,
    )
    part_style = ParagraphStyle(
        "Part", parent=chapter,
        fontSize=p.part_title_size_pt, leading=p.part_title_size_pt + 4,
        spaceBefore=1.5 * rl_inch, spaceAfter=0.2 * rl_inch,
    )
    title_style = ParagraphStyle("Title", parent=chapter, fontSize=24, leading=30, spaceBefore=1.2 * rl_inch)
    half_title = ParagraphStyle("HalfTitle", parent=chapter, fontName=regular, fontSize=19, leading=24, spaceBefore=2.45 * rl_inch)
    sub = ParagraphStyle("Sub", parent=styles["Normal"], fontName=italic, fontSize=10.5, leading=14, alignment=TA_CENTER)
    center = ParagraphStyle("Center", parent=body_first, alignment=TA_CENTER, firstLineIndent=0)
    small = ParagraphStyle("Small", parent=body_first, fontSize=8.5, leading=11, alignment=TA_LEFT)
    code_style = ParagraphStyle(
        "Code", parent=styles["Code"], fontName="Courier", fontSize=7.2, leading=9.1,
        leftIndent=0.12 * rl_inch, rightIndent=0.08 * rl_inch,
        spaceBefore=5, spaceAfter=7, borderPadding=6,
        borderWidth=0.4, borderColor=colors.HexColor("#B7BEC8"),
        backColor=colors.HexColor("#F3F5F7"),
    )
    list_style = ParagraphStyle(
        "List", parent=body_first, leftIndent=0.28 * rl_inch,
        firstLineIndent=0, bulletIndent=0.08 * rl_inch,
        spaceBefore=1, spaceAfter=2, alignment=TA_LEFT,
    )
    quote_style = ParagraphStyle(
        "Quote", parent=body_first, fontName=italic,
        leftIndent=0.3 * rl_inch, rightIndent=0.2 * rl_inch,
        borderWidth=0, borderPadding=0, spaceBefore=4, spaceAfter=5,
    )
    toc_title = ParagraphStyle("TOCTitle", parent=chapter, fontSize=17, leading=22, spaceBefore=0.3 * rl_inch, spaceAfter=0.2 * rl_inch)
    toc_part = ParagraphStyle("TOCPart", parent=body_first, fontName=bold, fontSize=10, leading=13, spaceBefore=8, spaceAfter=2)
    toc_item = ParagraphStyle("TOCItem", parent=body_first, fontSize=9.2, leading=11.5, leftIndent=0.16 * rl_inch, spaceBefore=0, spaceAfter=1)

    copyright_text = (
        f"Copyright © {html_module.escape(str(p.copyright_year))} {html_module.escape(p.author)}. "
        "All rights reserved.<br/><br/>"
        f"{html_module.escape(p.edition_statement)}<br/>"
        f"{html_module.escape(p.isbn)}<br/><br/>"
        f"{html_module.escape(p.creative_nonfiction_notice)}<br/><br/>"
        "No part of this book may be reproduced, distributed, or transmitted in any form or by any means "
        "without prior written permission, except for brief quotations in reviews, criticism, scholarship, "
        "or other uses permitted by law.<br/><br/>"
        f"Published by {html_module.escape(p.publisher)}"
    )

    story: list = [
        Paragraph(html_module.escape(p.title), half_title),
        PageBreak(),
        Paragraph(html_module.escape(p.title), title_style),
        Spacer(1, 0.12 * rl_inch),
        Paragraph(html_module.escape(p.subtitle), sub),
        Spacer(1, 0.35 * rl_inch),
        Paragraph(f"by {html_module.escape(p.author)}", center),
        PageBreak(),
        Spacer(1, 3.35 * rl_inch),
        Paragraph(copyright_text, small),
        PageBreak(),
    ]

    if p.dedication:
        ded = ParagraphStyle("Dedication", parent=sub, fontName=italic, fontSize=10.75, leading=15,
                             leftIndent=0.25 * rl_inch, rightIndent=0.25 * rl_inch, spaceBefore=2.35 * rl_inch)
        story.extend([Paragraph(html_module.escape(p.dedication), ded), PageBreak()])

    if p.epigraph_enabled and p.epigraph_text:
        ep = ParagraphStyle("Epigraph", parent=sub, fontName=italic, fontSize=10.5, leading=14,
                            leftIndent=0.3 * rl_inch, rightIndent=0.3 * rl_inch, spaceBefore=2.25 * rl_inch)
        ep_text = html_module.escape(p.epigraph_text)
        if p.epigraph_attribution:
            ep_text = f"{ep_text}<br/><br/>— {html_module.escape(p.epigraph_attribution)}"
        story.extend([Paragraph(ep_text, ep), PageBreak()])

    story.append(Paragraph("Contents", toc_title))
    for b in _contents_blocks(blocks):
        if b.level == 1:
            story.append(Paragraph(_md_inline(b.text), toc_part))
        else:
            label = b.text
            label = re.sub(r"^Chapter\s+(\d+)\.\s+", r"\1. ", label)
            story.append(Paragraph(_md_inline(label), toc_item))

    first_after_break = True
    for b in blocks:
        if b.kind == "heading":
            if b.level <= 2:
                story.append(PageBreak())
                style = part_style if b.text.lower().startswith("part ") else chapter
                story.append(Paragraph(_md_inline(b.text), style))
                first_after_break = True
            else:
                story.append(Spacer(1, 0.12 * rl_inch))
                story.append(Paragraph(f"<b>{_md_inline(b.text)}</b>", body_first))
                story.append(Spacer(1, 0.06 * rl_inch))
                first_after_break = True
            continue
        if b.kind == "scene_break":
            story.append(Spacer(1, 0.12 * rl_inch))
            story.append(Paragraph("*&nbsp;&nbsp;&nbsp;*&nbsp;&nbsp;&nbsp;*", center))
            story.append(Spacer(1, 0.12 * rl_inch))
            first_after_break = True
            continue
        if b.kind == "code":
            story.append(XPreformatted(html_module.escape(_wrap_code(b.text)), code_style))
            first_after_break = True
            continue
        if b.kind == "list_item":
            style = ParagraphStyle(
                f"ListLevel{b.level}", parent=list_style,
                leftIndent=(0.20 + 0.16 * b.level) * rl_inch,
                bulletIndent=(0.04 + 0.16 * b.level) * rl_inch,
            )
            story.append(Paragraph(_md_inline(b.text), style, bulletText=html_module.escape(b.marker or "•")))
            first_after_break = True
            continue
        if b.kind == "blockquote":
            story.append(Paragraph(_md_inline(b.text), quote_style))
            first_after_break = True
            continue
        style = body_first if first_after_break else body
        story.append(Paragraph(_md_inline(b.text), style))
        first_after_break = False

    # ReportLab otherwise seeds every page with its built-in Helvetica font,
    # leaving an unembedded font resource even when all visible text uses the
    # registered book face. Start the canvas with that embedded face instead.
    doc.build(story)
    return out_pdf

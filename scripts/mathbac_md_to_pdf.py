"""Render MATHBAC Proposers Day markdown deliverables to PDF via Playwright.

Usage: python scripts/mathbac_md_to_pdf.py
Output: docs/proposals/DARPA_MATHBAC/pdf/<name>.pdf
"""

from __future__ import annotations

import asyncio
import html
from pathlib import Path

import markdown
from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "docs" / "proposals" / "DARPA_MATHBAC"
OUT_DIR = SRC_DIR / "pdf"

TARGETS = [
    ("one_pager_v1.md", "SCBE_DAVA_MATHBAC_one_pager_v1.pdf"),
    ("elevator_pitches_v1.md", "SCBE_DAVA_MATHBAC_elevator_pitches_v1.pdf"),
    ("proposers_day_playbook.md", "SCBE_DAVA_MATHBAC_proposers_day_playbook_v1.pdf"),
    ("joint_memo_v1.md", "SCBE_DAVA_MATHBAC_joint_memo_v1.pdf"),
    ("v3_markup_for_collin.md", "SCBE_DAVA_MATHBAC_v3_markup_for_collin_v1.pdf"),
]

CSS = """
@page { size: Letter; margin: 0.75in 0.75in 0.85in 0.75in; }
body {
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #111;
  max-width: 100%;
}
h1 { font-size: 18pt; margin: 0 0 8pt 0; border-bottom: 2px solid #333; padding-bottom: 4pt; }
h2 { font-size: 13pt; margin: 14pt 0 6pt 0; color: #1a1a1a; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 11.5pt; margin: 10pt 0 4pt 0; color: #222; }
h4 { font-size: 10.5pt; margin: 8pt 0 3pt 0; color: #333; }
p { margin: 4pt 0; }
ul, ol { margin: 4pt 0 4pt 0; padding-left: 20pt; }
li { margin: 1pt 0; }
code {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 9pt;
  background: #f4f4f4;
  padding: 1pt 3pt;
  border-radius: 2pt;
}
pre {
  background: #f4f4f4;
  padding: 6pt 8pt;
  border-left: 3pt solid #888;
  font-size: 9pt;
  overflow-x: auto;
  page-break-inside: avoid;
}
pre code { background: transparent; padding: 0; }
table {
  border-collapse: collapse;
  margin: 6pt 0;
  width: 100%;
  font-size: 10pt;
  page-break-inside: avoid;
}
th, td { border: 1px solid #bbb; padding: 3pt 6pt; text-align: left; vertical-align: top; }
th { background: #e8e8e8; font-weight: 600; }
blockquote {
  border-left: 3pt solid #888;
  padding: 2pt 8pt;
  margin: 4pt 0;
  color: #444;
  font-style: italic;
}
hr { border: 0; border-top: 1px solid #888; margin: 10pt 0; }
strong { color: #000; }
a { color: #0a3d91; text-decoration: none; }
/* Prevent orphan headings */
h1, h2, h3, h4 { page-break-after: avoid; }
"""

HEADER_FOOTER = """
<div style="font-family: 'Segoe UI', sans-serif; font-size: 8pt; color: #666; width: 100%; padding: 0 0.75in;">
  <span>SCBE-AETHERMOORE &oplus; DAVA &mdash; DARPA MATHBAC TA1</span>
  <span style="float: right;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""


def md_to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "sane_lists",
            "toc",
        ],
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


async def render_one(page, src: Path, out: Path) -> None:
    md_text = src.read_text(encoding="utf-8")
    html_text = md_to_html(md_text, src.stem)
    await page.set_content(html_text, wait_until="load")
    await page.emulate_media(media="print")
    await page.pdf(
        path=str(out),
        format="Letter",
        print_background=True,
        display_header_footer=True,
        header_template="<div></div>",
        footer_template=HEADER_FOOTER,
        margin={"top": "0.75in", "bottom": "0.85in", "left": "0.75in", "right": "0.75in"},
    )
    print(f"  wrote {out.relative_to(REPO)}")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        for src_name, out_name in TARGETS:
            src = SRC_DIR / src_name
            if not src.exists():
                print(f"  skip (missing): {src_name}")
                continue
            out = OUT_DIR / out_name
            await render_one(page, src, out)
        await browser.close()
    print(f"Done. PDFs in {OUT_DIR.relative_to(REPO)}/")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CATALOG = DOCS / "research" / "research_catalog.json"
OUT_ROOT = DOCS / "research"
PAPERS = OUT_ROOT / "papers"
PDFS = PAPERS / "pdf"
TOPICS = OUT_ROOT / "topics"


BASE_CSS = """
:root {
  color-scheme: light;
  --ink: #17201d;
  --muted: #5b6762;
  --rule: #d8ded8;
  --paper: #fffdf7;
  --wash: #f3f6f0;
  --accent: #0f6f61;
  --gold: #8b6a16;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--wash);
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.58;
}
a { color: var(--accent); }
.shell {
  max-width: 1040px;
  margin: 0 auto;
  padding: 28px 20px 56px;
}
.paper {
  background: var(--paper);
  border: 1px solid var(--rule);
  box-shadow: 0 18px 45px rgba(23, 32, 29, 0.08);
  padding: 44px;
}
.kicker {
  color: var(--gold);
  font-family: Arial, sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
h1 {
  margin: 10px 0 10px;
  font-size: 36px;
  line-height: 1.08;
}
h2 {
  margin-top: 34px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--rule);
  font-size: 24px;
}
h3 { margin-top: 28px; font-size: 18px; }
p { margin: 12px 0; }
.subtitle, .abstract, .meta, .boundary {
  color: var(--muted);
}
.abstract, .boundary {
  border-left: 4px solid var(--accent);
  padding-left: 16px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
.card {
  display: block;
  min-height: 100%;
  padding: 18px;
  border: 1px solid var(--rule);
  background: #fff;
  text-decoration: none;
}
.card h3 { margin-top: 0; color: var(--ink); }
.card p { color: var(--muted); }
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}
.tag {
  border: 1px solid var(--rule);
  border-radius: 999px;
  padding: 3px 9px;
  color: var(--muted);
  background: #fff;
  font-family: Arial, sans-serif;
  font-size: 12px;
}
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 22px;
  font-family: Arial, sans-serif;
  font-size: 14px;
}
.source {
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid var(--rule);
  color: var(--muted);
  font-family: Arial, sans-serif;
  font-size: 13px;
}
pre, code {
  font-family: Consolas, "Courier New", monospace;
}
pre {
  overflow-x: auto;
  padding: 14px;
  border: 1px solid var(--rule);
  background: #f8faf7;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 18px 0;
  font-size: 14px;
}
th, td {
  border: 1px solid var(--rule);
  padding: 8px;
  vertical-align: top;
}
th { background: #f1f5ef; }
@media (max-width: 700px) {
  .paper { padding: 24px; }
  h1 { font-size: 28px; }
}
"""


def rel(path: str) -> Path:
    return DOCS / path


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def tags_html(tags: list[str]) -> str:
    return '<div class="tags">' + "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags) + "</div>"


def link(path: str, label: str, current: Path) -> str:
    target = DOCS / path
    href = Path(*([".."] * len(current.relative_to(DOCS).parts)), target.relative_to(DOCS)).as_posix()
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a>'


def page(title: str, body: str, current_dir: Path) -> str:
    nav = (
        '<nav class="nav">'
        f'{link("index.html", "Home", current_dir)}'
        f'{link("research/index.html", "Research Library", current_dir)}'
        f'{link("payments.html", "Payments", current_dir)}'
        "</nav>"
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f"<title>{html.escape(title)} | AetherMoore Research</title>\n"
        f"<style>{BASE_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="shell">\n'
        f"{nav}\n"
        '<main class="paper">\n'
        f"{body}\n"
        "</main>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def md_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_ul = False
    in_ol = False
    i = 0

    def flush_para() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph).strip()
            out.append(f"<p>{inline_md(text)}</p>")
            paragraph = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        if line.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                flush_para()
                close_lists()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if not line.strip():
            flush_para()
            close_lists()
            i += 1
            continue

        if is_table_start(lines, i):
            flush_para()
            close_lists()
            table, consumed = parse_table(lines[i:])
            out.append(table)
            i += consumed
            continue

        if line.startswith("#"):
            flush_para()
            close_lists()
            level = min(len(line) - len(line.lstrip("#")), 4)
            text = line[level:].strip()
            out.append(f"<h{level}>{inline_md(text)}</h{level}>")
            i += 1
            continue

        if line.startswith("- "):
            flush_para()
            if in_ol:
                close_lists()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_md(line[2:].strip())}</li>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            flush_para()
            if in_ul:
                close_lists()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s+", "", line)
            out.append(f"<li>{inline_md(item.strip())}</li>")
            i += 1
            continue

        close_lists()
        paragraph.append(line)
        i += 1

    flush_para()
    close_lists()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(out)


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    first = lines[index].strip()
    second = lines[index + 1].strip()
    return first.startswith("|") and first.endswith("|") and set(second.replace("|", "").replace(" ", "")) <= {"-", ":"}


def parse_table(lines: list[str]) -> tuple[str, int]:
    table_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            break
        table_lines.append(stripped)
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    body_rows = table_lines[2:]
    parts = ["<table><thead><tr>"]
    parts.extend(f"<th>{inline_md(cell)}</th>" for cell in headers)
    parts.append("</tr></thead><tbody>")
    for row in body_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        parts.append("<tr>")
        parts.extend(f"<td>{inline_md(cell)}</td>" for cell in cells)
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts), len(table_lines)


def paper_body(paper: dict[str, Any], source_html: str | None = None) -> str:
    links = []
    if paper.get("pdf"):
        links.append(link(paper["pdf"], "PDF", PAPERS))
    if paper.get("source_md"):
        links.append(link(paper["source_md"], "Source note", PAPERS))
    action = " | ".join(links)
    source_note = html.escape(paper.get("source_md", "catalog-only"))
    generator_note = "scripts/research/build_research_library.py"
    return f"""
<p class="kicker">AetherMoore Research Packet</p>
<h1>{html.escape(paper["title"])}</h1>
<p class="subtitle">{html.escape(paper.get("subtitle", ""))}</p>
{tags_html(paper.get("tags", []))}
<p class="abstract"><strong>Abstract.</strong> {html.escape(paper.get("abstract", ""))}</p>
<p class="boundary"><strong>Claim boundary.</strong> {html.escape(paper.get("claim_boundary", ""))}</p>
<p class="meta"><strong>Status:</strong> {html.escape(paper.get("status", ""))}</p>
<p class="meta"><strong>Research grade:</strong> {html.escape(paper.get("grade", "Unclassified"))}</p>
<p class="meta"><strong>Review model:</strong> {html.escape(paper.get("review_model", "Not recorded."))}</p>
<p class="meta">{action}</p>
<h2>Source Text</h2>
{source_html or "<p>See linked PDF/source note.</p>"}
<p class="source">Generated from <code>{source_note}</code> by <code>{generator_note}</code>.</p>
"""


def build_pages(catalog: dict[str, Any]) -> list[Path]:
    PAPERS.mkdir(parents=True, exist_ok=True)
    PDFS.mkdir(parents=True, exist_ok=True)
    TOPICS.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    topics = {topic["id"]: topic for topic in catalog["topics"]}

    cards = []
    for topic in catalog["topics"]:
        topic_papers = [p for p in catalog["papers"] if topic["id"] in p.get("topics", [p.get("topic")])]
        count = len(topic_papers)
        cards.append(
            f'<a class="card" href="topics/{html.escape(topic["id"])}.html">'
            f'<h3>{html.escape(topic["label"])}</h3>'
            f'<p>{html.escape(topic["description"])}</p>'
            f'{tags_html(topic.get("tags", []))}'
            f'<p>{count} packet{"s" if count != 1 else ""}</p>'
            "</a>"
        )
    index_intro = (
        "This page turns the loose research pile into a browsable, tagged library. "
        "Conversion here means research structure: topic framing, source ledger, "
        "review model, validation plan, claim boundary, and then HTML/PDF output. "
        "It is not just a file-format change."
    )
    standard_link = link(
        catalog.get("standard", "research/RESEARCH_PACKET_STANDARD.md"),
        "Read the research packet standard",
        OUT_ROOT,
    )
    all_cards = "".join(paper_card(p, OUT_ROOT) for p in catalog["papers"])
    index_body = f"""
<p class="kicker">AetherMoore Research Library</p>
<h1>Research packets by topic</h1>
<p class="abstract">{html.escape(index_intro)}</p>
<p>{standard_link}</p>
<div class="grid">{''.join(cards)}</div>
<h2>All Packets</h2>
<div class="grid">{all_cards}</div>
"""
    index_path = OUT_ROOT / "index.html"
    index_path.write_text(page("Research Library", index_body, OUT_ROOT), encoding="utf-8")
    written.append(index_path)

    for topic_id, topic in topics.items():
        topic_papers = [p for p in catalog["papers"] if topic_id in p.get("topics", [p.get("topic")])]
        topic_cards = (
            "".join(paper_card(p, TOPICS) for p in topic_papers)
            or "<p>No promoted packets yet. This topic lane is ready for notes.</p>"
        )
        body = f"""
<p class="kicker">Research Topic</p>
<h1>{html.escape(topic["label"])}</h1>
<p class="abstract">{html.escape(topic["description"])}</p>
{tags_html(topic.get("tags", []))}
<div class="grid">{topic_cards}</div>
"""
        path = TOPICS / f"{topic_id}.html"
        path.write_text(page(topic["label"], body, TOPICS), encoding="utf-8")
        written.append(path)

    for paper in catalog["papers"]:
        source_html = None
        source = paper.get("source_md")
        if source and rel(source).exists():
            source_html = md_to_html(rel(source).read_text(encoding="utf-8", errors="replace"))
        body = paper_body(paper, source_html)
        path = DOCS / paper["html"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page(paper["title"], body, path.parent), encoding="utf-8")
        written.append(path)

    return written


def paper_card(paper: dict[str, Any], current_dir: Path) -> str:
    href = link(paper["html"], paper["title"], current_dir)
    href_match = re.search(r'href="([^"]+)"', href)
    url = href_match.group(1) if href_match else paper["html"]
    pdf = ""
    if paper.get("pdf"):
        pdf = " " + link(paper["pdf"], "PDF", current_dir)
    return (
        f'<article class="card">'
        f'<h3><a href="{html.escape(url)}">{html.escape(paper["title"])}</a></h3>'
        f'<p>{html.escape(paper.get("subtitle", ""))}</p>'
        f'{tags_html(paper.get("tags", []))}'
        f'<p><strong>Status:</strong> {html.escape(paper.get("status", ""))}</p>'
        f'<p><strong>Grade:</strong> {html.escape(paper.get("grade", "Unclassified"))}</p>'
        f"<p>{href}{pdf}</p>"
        "</article>"
    )


async def render_pdfs(catalog: dict[str, Any]) -> list[Path]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - depends on local optional dependency
        raise RuntimeError(f"Playwright is required to render PDFs: {exc}") from exc

    rendered: list[Path] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page_obj = await browser.new_page(viewport={"width": 1000, "height": 1300})
        for paper in catalog["papers"]:
            if not paper.get("make_pdf"):
                continue
            html_path = DOCS / paper["html"]
            pdf_path = DOCS / paper["pdf"]
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            await page_obj.goto(html_path.resolve().as_uri(), wait_until="load")
            await page_obj.pdf(
                path=str(pdf_path),
                format="Letter",
                print_background=True,
                margin={
                    "top": "0.55in",
                    "right": "0.55in",
                    "bottom": "0.65in",
                    "left": "0.55in",
                },
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    '<div style="width:100%;font-size:9px;color:#6b6b6b;'
                    'padding:0 0.55in;display:flex;justify-content:space-between;">'
                    f'<span>{html.escape(paper["title"])}</span>'
                    '<span class="pageNumber"></span></div>'
                ),
            )
            rendered.append(pdf_path)
        await browser.close()
    return rendered


def validate(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    topics = {topic["id"] for topic in catalog.get("topics", [])}
    for paper in catalog.get("papers", []):
        missing_topics = [topic for topic in paper.get("topics", [paper.get("topic")]) if topic not in topics]
        if missing_topics:
            errors.append(f"{paper['id']}: unknown topics {missing_topics}")
        for key in ("source_md", "html"):
            if key in paper and not rel(paper[key]).exists():
                errors.append(f"{paper['id']}: missing {key} {paper[key]}")
        if paper.get("pdf") and not rel(paper["pdf"]).exists():
            errors.append(f"{paper['id']}: missing pdf {paper['pdf']}")
    for topic in catalog.get("topics", []):
        if not (TOPICS / f"{topic['id']}.html").exists():
            errors.append(f"{topic['id']}: missing topic page")
    if not (OUT_ROOT / "index.html").exists():
        errors.append("missing research/index.html")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AetherMoore static research library.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate generated outputs without regenerating.",
    )
    parser.add_argument("--no-pdf", action="store_true", help="Build HTML only.")
    args = parser.parse_args()

    catalog = load_catalog()
    if not args.check:
        written = build_pages(catalog)
        rendered: list[Path] = []
        if not args.no_pdf:
            rendered = asyncio.run(render_pdfs(catalog))
        print(f"wrote {len(written)} html files")
        print(f"rendered {len(rendered)} pdf files")
    errors = validate(catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("research library ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

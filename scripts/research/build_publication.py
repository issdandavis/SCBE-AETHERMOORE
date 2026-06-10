"""Publication builder — turn a curated markdown report into an official-format page.

This is the *publication tier* primitive: the place final drafts live as proper
documents (the thing arXiv/DARPA have and a pile of notes does not). It takes one
curated markdown file and emits:

  * ``<slug>.html``  — an official-format article page: title block (author /
    affiliation / date / stable document id), dated abstract, numbered sections, a
    references section, and an honest provenance footer. The page embeds two machine
    readouts of the same structure:
        - a ``TabManifest`` (JSON) — the agent / RAG self-index, reusing the governed
          browser-tab manifest layer; and
        - a schema.org ``ScholarlyArticle`` JSON-LD block — for search-engine crawlers.
  * ``<slug>.pdf``   — via pandoc (tectonic pdf-engine if available).
  * an append to ``index.json`` — the published-research index.

Honest-provenance discipline (not "verified"): the footer records author, version,
date, and a SHA-256 integrity hash. That proves the document is *untampered*, NOT that
its research is *correct* — exactly the claim arXiv makes (submitted / dated / versioned)
and no more. Do not relabel integrity as verification.

Zones: output defaults to ``artifacts/publications/`` (a build dir), NOT the public
``docs/`` Pages tree. Promotion to the public site is a separate, deliberate step gated
on real finished content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.aetherbrowser.tab_manifest import build_tab_manifest  # noqa: E402

DEFAULT_AUTHOR = "Issac Davis"
DEFAULT_AFFILIATION = "SCBE-AETHERMOORE / Spiralverse Research"
DEFAULT_OUT = Path("artifacts/publications")
_TECTONIC = Path("../devoted-novel/tools/bin/tectonic.exe")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "untitled"


def _parse_markdown(md: str, *, fallback_title: str) -> dict:
    """Split a markdown report into title / abstract / numbered sections / references."""
    lines = md.splitlines()
    title = fallback_title
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break

    body = "\n".join(lines[body_start:])
    # Sections are level-2 headings.
    parts = re.split(r"(?m)^##\s+(.+)$", body)
    lead = parts[0].strip()  # text before the first section == abstract candidate
    sections: list[tuple[str, str]] = []
    for j in range(1, len(parts), 2):
        heading = parts[j].strip()
        content = parts[j + 1].strip() if j + 1 < len(parts) else ""
        sections.append((heading, content))

    abstract = ""
    body_sections: list[tuple[str, str]] = []
    references = ""
    for heading, content in sections:
        low = heading.lower()
        if low in {"abstract", "summary"} and not abstract:
            abstract = content
        elif low in {"references", "bibliography", "citations"}:
            references = content
        else:
            body_sections.append((heading, content))
    if not abstract:
        abstract = lead

    return {
        "title": title,
        "abstract": _strip_blockquote(abstract),
        "sections": body_sections,
        "references": references,
    }


def _md_inline_to_html(text: str) -> str:
    """Minimal inline markdown -> HTML (escape first, then re-enable a few marks)."""
    out = escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    out = re.sub(r"\[(.+?)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)  # absolute or relative
    return out


def _strip_blockquote(text: str) -> str:
    """Drop leading markdown blockquote markers so a quoted lead reads as plain prose."""
    return "\n".join(line.lstrip("> ").rstrip() for line in text.splitlines()).strip()


def _block_to_html(content: str) -> str:
    html_parts: list[str] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("```"):  # fenced code/formula -> verbatim, like the PDF path
            inner = "\n".join(block.splitlines()[1:])
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3].rstrip("\n")
            html_parts.append(f"<pre><code>{escape(inner)}</code></pre>")
            continue
        if all(line.lstrip().startswith(("-", "*")) for line in block.splitlines()):
            items = "".join(f"<li>{_md_inline_to_html(li.lstrip('-* '))}</li>" for li in block.splitlines())
            html_parts.append(f"<ul>{items}</ul>")
        else:
            html_parts.append(f"<p>{_md_inline_to_html(block)}</p>")
    return "\n".join(html_parts)


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="author" content="{author}">
<meta name="citation_title" content="{title}">
<meta name="citation_author" content="{author}">
<meta name="citation_publication_date" content="{pub_date}">
<script type="application/ld+json">{jsonld}</script>
<script type="application/scbe-tab-manifest+json">{manifest}</script>
<style>
 body{{max-width:46rem;margin:3rem auto;padding:0 1.2rem;font:1rem/1.65 Georgia,'Times New Roman',serif;color:#1a1a1a}}
 h1{{font-size:1.7rem;line-height:1.3;margin:0 0 .4rem}}
 .meta{{color:#555;font-size:.95rem;margin-bottom:1.5rem}}
 .abstract{{background:#f6f6f4;border-left:3px solid #888;padding:.8rem 1rem;margin:1.5rem 0}}
 h2{{font-size:1.25rem;margin:2rem 0 .5rem;border-bottom:1px solid #e3e3e3;padding-bottom:.2rem}}
 code{{background:#f0f0ee;padding:.05rem .3rem;border-radius:3px;font-size:.9em}}
 pre{{background:#f6f6f4;border:1px solid #e3e3e3;border-radius:4px;padding:.7rem 1rem}}
 pre{{overflow-x:auto;font-size:.85rem;line-height:1.45}}
 pre code{{background:none;padding:0}}
 .prov{{margin-top:3rem;padding-top:1rem;border-top:1px solid #ddd;color:#666;font-size:.85rem}}
 .prov code{{word-break:break-all}}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">{author} &middot; {affiliation} &middot; {pub_date} &middot; <code>{doc_id}</code></div>
<div class="abstract"><strong>Abstract.</strong> {abstract}</div>
{sections}
{references}
<div class="prov">
<strong>Provenance.</strong> Author: {author}. Version: {version}. Date: {pub_date}.
SHA-256 integrity: <code>{sha256}</code>.<br>
This stamp proves the document is unaltered (integrity), not that its findings are correct
(no peer review is claimed).
</div>
</body>
</html>
"""


def build_publication(
    source: Path,
    *,
    out_dir: Path,
    author: str,
    affiliation: str,
    version: str,
    pub_date: str,
) -> dict:
    md = source.read_text(encoding="utf-8")
    sha256 = hashlib.sha256(md.encode("utf-8")).hexdigest()
    parsed = _parse_markdown(md, fallback_title=source.stem.replace("_", " "))
    slug = _slugify(parsed["title"])
    doc_id = f"{slug}-{sha256[:8]}"

    sections_html = ""
    for n, (heading, content) in enumerate(parsed["sections"], start=1):
        heading = re.sub(r"^\d+[.)]\s*", "", heading)  # avoid "1. 1." when source pre-numbers
        sections_html += f"<h2>{n}. {escape(heading)}</h2>\n{_block_to_html(content)}\n"
    references_html = ""
    if parsed["references"]:
        references_html = f"<h2>References</h2>\n{_block_to_html(parsed['references'])}"

    jsonld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "ScholarlyArticle",
            "headline": parsed["title"],
            "author": {"@type": "Person", "name": author, "affiliation": affiliation},
            "datePublished": pub_date,
            "version": version,
            "identifier": doc_id,
            "abstract": parsed["abstract"][:1000],
        },
        ensure_ascii=False,
    )

    # Self-index: reuse the governed tab-manifest layer on the rendered article.
    inner = f"<html><head><title>{escape(parsed['title'])}</title></head><body>" + sections_html + "</body></html>"
    manifest = build_tab_manifest(f"https://issdandavis.github.io/papers/{slug}.html", inner, fetched_at=0.0)
    manifest_json = json.dumps(manifest.to_context_dict(), ensure_ascii=False)

    html = _HTML_TEMPLATE.format(
        title=escape(parsed["title"]),
        author=escape(author),
        affiliation=escape(affiliation),
        pub_date=pub_date,
        doc_id=doc_id,
        version=escape(version),
        sha256=sha256,
        abstract=_md_inline_to_html(parsed["abstract"][:1500]),
        sections=sections_html,
        references=references_html,
        jsonld=jsonld,
        manifest=manifest_json,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{slug}.html"
    html_path.write_text(html, encoding="utf-8")

    pdf_path = out_dir / f"{slug}.pdf"
    pdf_status = _render_pdf(source, pdf_path)

    record = {
        "doc_id": doc_id,
        "title": parsed["title"],
        "slug": slug,
        "author": author,
        "version": version,
        "date": pub_date,
        "sha256": sha256,
        "html": str(html_path),
        "pdf": str(pdf_path) if pdf_status["ok"] else None,
        "manifest_tokens": manifest.token_estimate,
        "section_count": len(parsed["sections"]),
        "has_references": bool(parsed["references"]),
        "checklist": _officialness_checklist(parsed, pdf_status),
    }
    _append_index(out_dir / "index.json", record)
    record["pdf_status"] = pdf_status
    return record


def _render_pdf(source: Path, pdf_path: Path) -> dict:
    pandoc = shutil.which("pandoc") or str(Path.home() / "AppData/Local/Pandoc/pandoc.exe")
    if not Path(pandoc).exists() and not shutil.which("pandoc"):
        return {"ok": False, "reason": "pandoc not found"}
    cmd = [pandoc, str(source), "-o", str(pdf_path), "--standalone"]
    if _TECTONIC.exists():
        cmd += [f"--pdf-engine={_TECTONIC}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "reason": f"pandoc failed: {exc}"}
    if proc.returncode != 0:
        return {"ok": False, "reason": proc.stderr.strip()[:400] or "pandoc nonzero exit"}
    return {"ok": pdf_path.exists(), "engine": "tectonic" if _TECTONIC.exists() else "pandoc-default"}


def _officialness_checklist(parsed: dict, pdf_status: dict) -> dict:
    """Structural checklist — what makes a page read 'official'. Honest about gaps."""
    return {
        "title_block": True,
        "dated_abstract": bool(parsed["abstract"]),
        "numbered_sections": len(parsed["sections"]) > 0,
        "references_section": bool(parsed["references"]),
        "figures_with_captions": False,  # source notes carry no figures yet
        "stable_document_id": True,
        "honest_provenance": True,  # author/version/date/hash, NOT "verified"
        "schema_org_jsonld": True,
        "self_index_manifest": True,
        "rendered_pdf": pdf_status.get("ok", False),
    }


def _append_index(index_path: Path, record: dict) -> None:
    existing: list[dict] = []
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing = [r for r in existing if r.get("slug") != record["slug"]]  # republish replaces by slug
    existing.append({k: v for k, v in record.items() if k != "pdf_status"})
    index_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an official-format publication from a markdown report")
    parser.add_argument("source", type=Path, help="Curated markdown report")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--author", default=DEFAULT_AUTHOR)
    parser.add_argument("--affiliation", default=DEFAULT_AFFILIATION)
    parser.add_argument("--version", default="v1")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)

    if not args.source.exists():
        print(json.dumps({"ok": False, "error": f"no such file: {args.source}"}))
        return 1

    record = build_publication(
        args.source,
        out_dir=args.out_dir,
        author=args.author,
        affiliation=args.affiliation,
        version=args.version,
        pub_date=args.date,
    )
    print(json.dumps({"ok": True, **record}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Map every published HTML page to its GitHub source and add shared source chrome."""

from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
REPOSITORY = "issdandavis/SCBE-AETHERMOORE"
BRANCH = "main"
PUBLIC_BASE = "https://aethermoore.com/"
SOURCE_BASE = f"https://github.com/{REPOSITORY}/blob/{BRANCH}/"
MAP_FILENAME = "github-map.html"
MAP_JSON_FILENAME = "github-map.json"
SOURCE_SCRIPT = "assets/source-map.js"
SOURCE_TAG_RE = re.compile(r"\s*<script\b[^>]*\bdata-aether-source=(?:\"[^\"]*\"|'[^']*')[^>]*></script>", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
VERIFY_FILE_RE = re.compile(r"^google[0-9a-f]+\.html$", re.I)


@dataclass(frozen=True)
class PageRecord:
    title: str
    category: str
    public_path: str
    public_url: str
    source_path: str
    source_url: str
    raw_url: str


def page_title(text: str, fallback: str) -> str:
    match = TITLE_RE.search(text)
    if not match:
        return fallback
    title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return title or fallback


def public_path_for(relative: str) -> str:
    if relative == "index.html":
        return ""
    if relative.endswith("/index.html"):
        return relative[: -len("index.html")]
    return relative


def build_record(path: Path, docs_root: Path) -> PageRecord:
    relative = path.relative_to(docs_root).as_posix()
    text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
    title = "GitHub Page Map" if relative == MAP_FILENAME else page_title(text, path.stem.replace("-", " ").title())
    public_path = public_path_for(relative)
    source_path = f"docs/{relative}"
    category = relative.split("/", 1)[0] if "/" in relative else "root"
    return PageRecord(
        title=title,
        category=category,
        public_path=public_path,
        public_url=PUBLIC_BASE + quote(public_path, safe="/"),
        source_path=source_path,
        source_url=SOURCE_BASE + quote(source_path, safe="/"),
        raw_url=f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}/" + quote(source_path, safe="/"),
    )


def discover_pages(docs_root: Path) -> list[Path]:
    return sorted(
        path
        for path in docs_root.rglob("*.html")
        if path.is_file() and not VERIFY_FILE_RE.match(path.name)
    )


def source_tag(path: Path, docs_root: Path) -> str:
    relative = path.relative_to(docs_root).as_posix()
    asset_path = posixpath.relpath(SOURCE_SCRIPT, posixpath.dirname(relative) or ".")
    return (
        f'<script defer src="{asset_path}" '
        f'data-aether-source="docs/{html.escape(relative, quote=True)}"></script>'
    )


def inject_source_tag(path: Path, docs_root: Path) -> bool:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace")
    if "</body>" not in text.lower():
        return False
    newline = "\r\n" if "\r\n" in text else "\n"
    tag = source_tag(path, docs_root)
    cleaned = SOURCE_TAG_RE.sub("", text)
    body_match = re.search(r"</body>", cleaned, re.I)
    if body_match is None:
        return False
    line_start = cleaned.rfind("\n", 0, body_match.start()) + 1
    body_indent = cleaned[line_start : body_match.start()]
    if body_indent.strip():
        body_indent = ""
        line_start = body_match.start()
    # robot.html is the only tracked CRLF source file. Git treats CR on a newly
    # inserted line there as trailing whitespace, so keep that injected line LF.
    tag_newline = "\n" if path.name == "robot.html" and newline == "\r\n" else newline
    updated = (
        cleaned[:line_start].rstrip()
        + newline
        + body_indent
        + tag
        + tag_newline
        + body_indent
        + cleaned[body_match.start() :]
    )
    if path.name != "robot.html":
        updated = updated.replace("\r\n", "\n").replace("\r", "\n")
        if newline == "\r\n":
            updated = updated.replace("\n", "\r\n")
    encoded = updated.encode("utf-8")
    if has_bom:
        encoded = b"\xef\xbb\xbf" + encoded
    if encoded == raw:
        return False
    path.write_bytes(encoded)
    return True


def render_source_script() -> str:
    return r'''(function () {
  "use strict";
  if (document.getElementById("aether-source-map-host")) return;
  var script = document.currentScript;
  var sourcePath = script && script.dataset ? script.dataset.aetherSource : "docs/index.html";
  var repo = "https://github.com/issdandavis/SCBE-AETHERMOORE";
  var sourceUrl = repo + "/blob/main/" + sourcePath.split("/").map(encodeURIComponent).join("/");
  var scriptUrl = script && script.src ? new URL(script.src, document.baseURI) : new URL("assets/source-map.js", document.baseURI);
  var mapUrl = new URL("../github-map.html", scriptUrl).href;
  var host = document.createElement("div");
  host.id = "aether-source-map-host";
  host.setAttribute("data-source-path", sourcePath);
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
  root.innerHTML = [
    "<style>",
    ":host{all:initial}",
    ".map{position:fixed;left:14px;bottom:14px;z-index:2147483000;display:flex;align-items:center;gap:2px;padding:4px;border:1px solid rgba(244,239,228,.18);border-radius:999px;background:rgba(8,10,12,.9);box-shadow:0 18px 60px rgba(0,0,0,.38);backdrop-filter:blur(16px);font:700 11px/1.1 ui-monospace,SFMono-Regular,Cascadia Mono,Consolas,monospace}",
    ".map:before{content:'GH';display:grid;place-items:center;width:28px;height:28px;border-radius:50% 44% 48% 42%;color:#17100d;background:#d9825b;font-weight:950;transform:rotate(-5deg)}",
    "a{display:inline-flex;align-items:center;min-height:28px;padding:0 9px;border-radius:999px;color:#f4efe4;text-decoration:none;white-space:nowrap}",
    "a:hover,a:focus-visible{color:#ffd0b9;background:rgba(217,130,91,.13);outline:none}",
    ".path{max-width:0;overflow:hidden;color:#a8b3ad;opacity:0;transition:max-width .18s ease,opacity .18s ease}",
    ".map:hover .path,.map:focus-within .path{max-width:240px;opacity:1}",
    "@media(max-width:560px){.map{left:8px;bottom:8px}.path{display:none}a{padding:0 7px}}",
    "@media(prefers-reduced-motion:reduce){.path{transition:none}}",
    "</style>",
    "<nav class='map' aria-label='Page source map'>",
    "<a href='" + sourceUrl + "' target='_blank' rel='noreferrer'>Source <span class='path'>&nbsp;/ " + sourcePath + "</span></a>",
    "<a href='" + mapUrl + "'>All pages</a>",
    "</nav>"
  ].join("");
  document.documentElement.appendChild(host);
})();
'''


def render_map_html(pages: list[PageRecord]) -> str:
    cards = []
    for page in pages:
        search = html.escape(f"{page.title} {page.category} {page.public_path}".lower(), quote=True)
        cards.append(
            f'''<article class="page-card" data-search="{search}">
  <div><span>{html.escape(page.category)}</span><h2>{html.escape(page.title)}</h2></div>
  <code>/{html.escape(page.public_path)}</code>
  <nav><a href="{html.escape(page.public_url, quote=True)}">Open page</a><a href="{html.escape(page.source_url, quote=True)}">GitHub source</a></nav>
</article>'''
        )
    cards_html = "\n".join(cards)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Every public AetherMoore page mapped to its source in the SCBE-AETHERMOORE GitHub repository." />
  <title>GitHub Page Map - AetherMoore</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080a0c; --pane:#111313; --ink:#f4efe4; --muted:#a6b0aa; --line:rgba(244,239,228,.14); --clay:#d9825b; --cobalt:#7f9ee8; font-family:"Segoe UI Variable","Segoe UI",sans-serif; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; min-width:320px; color:var(--ink); background:radial-gradient(circle at 8% 8%,rgba(217,130,91,.16),transparent 30rem),radial-gradient(circle at 92% 30%,rgba(127,158,232,.1),transparent 34rem),linear-gradient(180deg,#07090b,#101110 60%,#07090b); }}
    a {{ color:inherit; text-decoration:none; }}
    a:focus-visible,input:focus-visible {{ outline:2px solid var(--clay); outline-offset:3px; }}
    header,main,footer {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; }}
    header {{ padding:82px 0 34px; }}
    .eyebrow {{ margin:0 0 16px; color:var(--clay); font:800 12px/1.2 ui-monospace,Consolas,monospace; letter-spacing:.14em; text-transform:uppercase; }}
    h1 {{ max-width:900px; margin:0; font-size:clamp(54px,9vw,124px); line-height:.84; letter-spacing:-.085em; }}
    .lede {{ max-width:760px; margin:26px 0 0; color:var(--muted); font-size:20px; line-height:1.5; }}
    .toolbar {{ position:sticky; top:12px; z-index:10; display:grid; grid-template-columns:1fr auto; gap:10px; margin:0 0 18px; padding:8px; border:1px solid var(--line); border-radius:999px; background:rgba(8,10,12,.84); backdrop-filter:blur(16px); }}
    input {{ width:100%; min-height:46px; border:0; border-radius:999px; color:var(--ink); background:rgba(255,255,255,.045); padding:0 18px; font:650 14px/1 ui-monospace,Consolas,monospace; }}
    .count {{ display:grid; place-items:center; min-width:130px; border-radius:999px; color:#1b100c; background:var(--clay); font-weight:900; }}
    .page-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; padding-bottom:80px; }}
    .page-card {{ min-height:230px; display:flex; flex-direction:column; justify-content:space-between; gap:18px; border:1px solid var(--line); border-radius:28px 18px 31px 20px; background:linear-gradient(145deg,rgba(217,130,91,.075),rgba(127,158,232,.035)),rgba(17,19,19,.76); padding:22px; box-shadow:0 20px 60px rgba(0,0,0,.2); }}
    .page-card:hover {{ border-color:rgba(217,130,91,.42); transform:translateY(-2px); }}
    .page-card span {{ color:var(--clay); font:800 10px/1 ui-monospace,Consolas,monospace; letter-spacing:.12em; text-transform:uppercase; }}
    .page-card h2 {{ margin:14px 0 0; font-size:25px; line-height:1; letter-spacing:-.045em; }}
    .page-card code {{ color:var(--muted); font:600 11px/1.35 ui-monospace,Consolas,monospace; overflow-wrap:anywhere; }}
    .page-card nav {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .page-card nav a {{ min-height:38px; display:inline-flex; align-items:center; border:1px solid var(--line); border-radius:999px; padding:0 12px; font-size:12px; font-weight:800; }}
    .page-card nav a:last-child {{ color:#1b100c; background:var(--clay); border-color:var(--clay); }}
    footer {{ border-top:1px solid var(--line); padding:26px 0 60px; color:var(--muted); }}
    @media(max-width:900px) {{ .page-grid{{grid-template-columns:1fr 1fr;}} }}
    @media(max-width:620px) {{ header{{padding-top:54px}} .toolbar{{grid-template-columns:1fr;border-radius:22px}} .count{{min-height:38px}} .page-grid{{grid-template-columns:1fr}} }}
    @media(prefers-reduced-motion:reduce) {{ html{{scroll-behavior:auto}} .page-card{{transition:none}} }}
  </style>
</head>
<body>
  <header>
    <p class="eyebrow">AetherMoore / open-source surface</p>
    <h1>Every page has a source.</h1>
    <p class="lede">Search the complete public website, open the live page, or jump directly to the file that builds it in <a href="https://github.com/{REPOSITORY}">{REPOSITORY}</a>.</p>
  </header>
  <main>
    <div class="toolbar"><input id="page-search" type="search" placeholder="Search pages, sections, or paths" aria-label="Search mapped pages" /><span class="count" id="page-count">{len(pages)} pages</span></div>
    <section class="page-grid" id="page-grid" aria-live="polite">{cards_html}</section>
  </main>
  <footer>Generated from <code>docs/**/*.html</code> by <code>scripts/system/build_public_github_map.py</code>.</footer>
  <script>
    (function() {{
      var input=document.getElementById('page-search');
      var cards=Array.prototype.slice.call(document.querySelectorAll('.page-card'));
      var count=document.getElementById('page-count');
      input.addEventListener('input',function(){{
        var query=input.value.trim().toLowerCase();
        var visible=0;
        cards.forEach(function(card){{var show=!query||card.dataset.search.indexOf(query)!==-1;card.hidden=!show;if(show)visible+=1;}});
        count.textContent=visible+' page'+(visible===1?'':'s');
      }});
    }})();
  </script>
<script defer src="assets/source-map.js" data-aether-source="docs/github-map.html"></script>
</body>
</html>
'''


def render_sitemap(pages: list[PageRecord]) -> str:
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages:
        rows.append(f"  <url><loc>{html.escape(page.public_url)}</loc></url>")
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def build_public_github_map(docs_root: Path = DOCS_ROOT) -> dict[str, int | str]:
    docs_root.mkdir(parents=True, exist_ok=True)
    map_path = docs_root / MAP_FILENAME
    if not map_path.exists():
        map_path.write_text("<!doctype html><title>GitHub Page Map</title><body></body>\n", encoding="utf-8")
    initial_pages = [build_record(path, docs_root) for path in discover_pages(docs_root)]
    map_path.write_text(render_map_html(initial_pages), encoding="utf-8")

    page_paths = discover_pages(docs_root)
    pages = [build_record(path, docs_root) for path in page_paths]
    (docs_root / "assets").mkdir(parents=True, exist_ok=True)
    (docs_root / SOURCE_SCRIPT).write_text(render_source_script(), encoding="utf-8")
    (docs_root / MAP_JSON_FILENAME).write_text(
        json.dumps(
            {
                "schema": "aethermoore_github_page_map_v1",
                "repository": REPOSITORY,
                "branch": BRANCH,
                "page_count": len(pages),
                "pages": [asdict(page) for page in pages],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (docs_root / "sitemap.xml").write_text(render_sitemap(pages), encoding="utf-8")

    updated = sum(1 for path in page_paths if inject_source_tag(path, docs_root))
    return {"schema": "aethermoore_github_page_map_build_v1", "pages": len(pages), "updated": updated}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_public_github_map(args.docs_root.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

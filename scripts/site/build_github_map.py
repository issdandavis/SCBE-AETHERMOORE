"""Build the public AetherMoore page-to-GitHub source map."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "github-map.html"
LIVE_ROOT = "https://aethermoore.com"
SOURCE_ROOT = "https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class Page:
    path: str
    title: str
    live_url: str
    source_url: str


def _title(path: Path) -> str:
    if path == OUTPUT and not path.exists():
        return "AetherMoore GitHub Page Map"
    match = TITLE_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if match:
        return html.unescape(" ".join(match.group(1).split()))
    return path.stem.replace("-", " ").title()


def _live_path(relative: Path) -> str:
    value = relative.as_posix()
    if value == "index.html":
        return "/"
    if value.endswith("/index.html"):
        return f"/{value.removesuffix('index.html')}"
    return f"/{value}"


def pages() -> list[Page]:
    paths = set(DOCS.rglob("*.html"))
    paths.add(OUTPUT)
    result = []
    for path in sorted(paths, key=lambda item: item.relative_to(DOCS).as_posix()):
        relative = path.relative_to(DOCS)
        docs_path = (Path("docs") / relative).as_posix()
        result.append(
            Page(
                path=docs_path,
                title=_title(path),
                live_url=f"{LIVE_ROOT}{_live_path(relative)}",
                source_url=f"{SOURCE_ROOT}/{docs_path}",
            )
        )
    return result


def render(items: list[Page]) -> str:
    rows = "\n".join(f"""          <tr>
            <td><a href="{html.escape(item.live_url)}">{html.escape(item.title)}</a></td>
            <td><code>{html.escape(item.path)}</code></td>
            <td><a href="{html.escape(item.source_url)}">View source</a></td>
          </tr>""" for item in items)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AetherMoore GitHub Page Map</title>
    <meta
      name="description"
      content="A complete map from every public AetherMoore HTML page to its versioned GitHub source."
    />
    <style>
      :root {{
        color-scheme: dark;
        --bg: #090d10;
        --panel: #12191d;
        --line: #354247;
        --text: #f7f0e2;
        --muted: #aeb9b7;
        --gold: #e0bb68;
        --green: #22c79a;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font: 16px/1.5 Inter, ui-sans-serif, system-ui, sans-serif;
      }}
      main {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 52px 0 72px; }}
      a {{ color: var(--gold); }}
      h1 {{ margin: 10px 0 8px; font-size: clamp(34px, 6vw, 64px); line-height: 1; }}
      .eyebrow {{
        color: var(--green);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
      }}
      .summary {{ max-width: 760px; color: var(--muted); }}
      .count {{
        display: inline-block;
        margin: 18px 0 28px;
        padding: 8px 12px;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--green);
      }}
      .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{
        padding: 13px 16px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
      }}
      th {{
        position: sticky;
        top: 0;
        background: #172226;
        color: var(--muted);
        font-size: 12px;
        letter-spacing: .08em;
        text-transform: uppercase;
      }}
      tr:last-child td {{ border-bottom: 0; }}
      code {{ color: var(--muted); white-space: nowrap; }}
      .back {{ display: inline-block; margin-top: 24px; }}
      @media (max-width: 700px) {{
        main {{ width: min(100% - 20px, 1180px); padding-top: 30px; }}
        th, td {{ padding: 11px 12px; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <div class="eyebrow">Public source inventory</div>
      <h1>GitHub page map</h1>
      <p class="summary">
        Every deployed HTML surface is paired with its canonical live URL and versioned source location.
        This page is generated from <code>docs/</code>, so omissions fail validation.
      </p>
      <div class="count">{len(items)} / {len(items)} pages mapped</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Public page</th><th>Repository path</th><th>GitHub</th></tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div>
      <a class="back" href="/">Back to AetherMoore</a>
    </main>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render(pages())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("docs/github-map.html is missing or stale; run with --write")
    else:
        OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(f"github page map: {len(pages())}/{len(pages())} HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

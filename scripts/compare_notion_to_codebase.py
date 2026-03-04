#!/usr/bin/env python3
"""
Compare local Notion export pages against the repository codebase.

Inputs:
  - training-data/notion_raw_clean.jsonl

Outputs:
  - training/notion_codebase_comparison.json
  - training/NOTION_CODEBASE_COMPARISON.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "not", "all", "via", "use", "using", "how", "what", "when", "where",
    "why", "its", "our", "their", "have", "has", "had", "was", "were", "will",
    "can", "could", "should", "would", "about", "into", "also", "more", "than",
    "layer", "layers", "system", "systems", "page", "pages", "overview", "guide",
    "template", "templates", "project", "projects", "status", "complete",
}

TEXT_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml"}
EXCLUDE_SUBSTRINGS = {
    "/archive/",
    "/dist/",
    "/node_modules/",
    "/training-data/",
    "/artifacts/",
    "/.git/",
}


@dataclass
class NotionRecord:
    page_id: str
    title: str
    text: str
    categories: list[str]
    url: str


@dataclass
class CodeDoc:
    path: str
    tokens: set[str]
    weight: float


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


def load_notion(path: Path) -> list[NotionRecord]:
    records: list[NotionRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            text = str(raw.get("text", ""))
            title = str(raw.get("title", "Untitled"))
            records.append(
                NotionRecord(
                    page_id=str(raw.get("id", "")),
                    title=title,
                    text=text,
                    categories=list(raw.get("categories", [])),
                    url=str(raw.get("url", "")),
                )
            )
    return records


def iter_code_files(repo_root: Path) -> list[Path]:
    roots = ["src", "hydra", "scripts", "docs", "training", "api", "packages"]
    files: list[Path] = []
    for root in roots:
        p = repo_root / root
        if not p.exists():
            continue
        for fp in p.rglob("*"):
            if not fp.is_file():
                continue
            if fp.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            norm = str(fp).replace("\\", "/").lower()
            if any(x in norm for x in EXCLUDE_SUBSTRINGS):
                continue
            files.append(fp)
    return files


def load_code_docs(repo_root: Path, max_chars: int = 250_000) -> list[CodeDoc]:
    docs: list[CodeDoc] = []
    for fp in iter_code_files(repo_root):
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        text = text[:max_chars]
        toks = set(tokenize(text))
        if not toks:
            continue
        rel = str(fp.relative_to(repo_root)).replace("\\", "/")
        rel_lower = rel.lower()
        if rel_lower.startswith(("src/", "hydra/", "api/")):
            weight = 1.45
        elif rel_lower.startswith("scripts/"):
            weight = 1.25
        elif rel_lower.startswith("docs/"):
            weight = 1.0
        else:
            weight = 0.9
        docs.append(CodeDoc(path=rel, tokens=toks, weight=weight))
    return docs


def score_page_to_doc(
    page_title_tokens: set[str],
    page_body_tokens: set[str],
    doc_tokens: set[str],
    doc_weight: float,
) -> float:
    title_overlap = len(page_title_tokens & doc_tokens)
    body_overlap = len(page_body_tokens & doc_tokens)
    return ((3.0 * title_overlap) + body_overlap) * doc_weight


def compare(records: list[NotionRecord], docs: list[CodeDoc], top_k: int = 5) -> list[dict]:
    output: list[dict] = []
    for rec in records:
        title_tokens = set(tokenize(rec.title))
        body_tokens = set(tokenize(rec.text[:4000]))
        if not title_tokens and not body_tokens:
            continue

        scored: list[tuple[float, str]] = []
        for doc in docs:
            s = score_page_to_doc(title_tokens, body_tokens, doc.tokens, doc.weight)
            if s > 0:
                scored.append((s, doc.path))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [{"path": p, "score": round(s, 3)} for s, p in scored[:top_k]]
        best_score = top[0]["score"] if top else 0.0
        output.append(
            {
                "id": rec.page_id,
                "title": rec.title,
                "categories": rec.categories,
                "url": rec.url,
                "best_score": best_score,
                "matches": top,
            }
        )
    return output


def build_markdown_report(comparison: list[dict], output_path: Path) -> None:
    total = len(comparison)
    matched = sum(1 for r in comparison if r["best_score"] > 0)
    low = [r for r in comparison if r["best_score"] <= 2]
    high = sorted(comparison, key=lambda x: x["best_score"], reverse=True)[:40]

    cat_counter = Counter()
    for r in comparison:
        for c in r.get("categories", []):
            cat_counter[c] += 1

    lines: list[str] = []
    lines.append("# Notion -> Codebase Comparison")
    lines.append("")
    lines.append(f"- Total Notion pages analyzed: **{total}**")
    lines.append(f"- Pages with at least one codebase match: **{matched}**")
    lines.append(f"- Low-coverage pages (best score <= 2): **{len(low)}**")
    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    if cat_counter:
        for cat, count in cat_counter.most_common():
            lines.append(f"- {cat}: {count}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Top Matched Pages")
    lines.append("")
    for row in high:
        lines.append(f"### {row['title']}")
        lines.append(f"- Best score: `{row['best_score']}`")
        if row.get("url"):
            lines.append(f"- URL: {row['url']}")
        for m in row["matches"][:3]:
            lines.append(f"- Match: `{m['path']}` (score `{m['score']}`)")
        lines.append("")

    lines.append("## Low Coverage Pages (Need Manual Mapping)")
    lines.append("")
    for row in low[:120]:
        lines.append(f"- {row['title']} (best score `{row['best_score']}`)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Notion export pages to codebase files")
    parser.add_argument(
        "--notion-jsonl",
        default="training-data/notion_raw_clean.jsonl",
        help="Path to local Notion export JSONL",
    )
    parser.add_argument(
        "--output-json",
        default="training/notion_codebase_comparison.json",
        help="Output JSON mapping file",
    )
    parser.add_argument(
        "--output-md",
        default="training/NOTION_CODEBASE_COMPARISON.md",
        help="Output markdown report",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top matches per page",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    notion_path = repo_root / args.notion_jsonl
    if not notion_path.exists():
        raise FileNotFoundError(f"Notion JSONL not found: {notion_path}")

    records = load_notion(notion_path)
    docs = load_code_docs(repo_root)
    comparison = compare(records, docs, top_k=args.top_k)

    out_json = repo_root / args.output_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md = repo_root / args.output_md
    build_markdown_report(comparison, out_md)

    print(
        json.dumps(
            {
                "notion_pages": len(records),
                "code_docs": len(docs),
                "compared": len(comparison),
                "output_json": str(out_json).replace("\\", "/"),
                "output_md": str(out_md).replace("\\", "/"),
            }
        )
    )


if __name__ == "__main__":
    main()

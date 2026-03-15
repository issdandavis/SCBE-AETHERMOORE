#!/usr/bin/env python3
"""Scan official government-contracting portals and rank keyword relevance."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from scripts.system.html_text import html_to_text


DEFAULT_SOURCES = [
    ("sam_contract_opportunities", "https://sam.gov/content/opportunities"),
    ("diu_open_solicitations", "https://www.diu.mil/work-with-us/open-solicitations"),
    ("afwerx_open_topic", "https://afwerx.com/divisions/ventures/open-topic/"),
    ("sbir_funding", "https://www.sbir.gov/funding"),
    ("usaspending_search", "https://www.usaspending.gov/search"),
    ("far_part_12", "https://www.acquisition.gov/far/part-12"),
]


@dataclass
class SourceResult:
    source: str
    url: str
    status: str
    title: str
    score: int
    keyword_hits: dict[str, int]
    error: str | None = None


def _parse_keywords(raw: str) -> list[str]:
    items = [x.strip().lower() for x in raw.split(",")]
    return [x for x in items if x]


def _extract_title(html_text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _to_text(html_text: str) -> str:
    return html_to_text(html_text, lower=True)


def _resolve_output_dir(raw_path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    target = (repo_root / raw_path).resolve()
    artifacts_root = (repo_root / "artifacts").resolve()
    if target != artifacts_root and artifacts_root not in target.parents:
        raise ValueError("output path must stay under artifacts/")
    return target


def _count_hits(text: str, keywords: Iterable[str]) -> dict[str, int]:
    hits: dict[str, int] = {}
    for key in keywords:
        hits[key] = text.count(key)
    return hits


def _fetch(url: str, timeout: int) -> tuple[str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "scbe-gov-contract-scan/1.0 (+https://github.com/issdandavis/SCBE-AETHERMOORE)"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html_text = response.read().decode(charset, errors="replace")
        return str(response.status), html_text


def run_scan(keywords: list[str], timeout: int, extra_urls: list[str]) -> list[SourceResult]:
    sources = list(DEFAULT_SOURCES)
    for idx, url in enumerate(extra_urls, start=1):
        sources.append((f"extra_{idx}", url))

    results: list[SourceResult] = []
    for source_name, url in sources:
        try:
            status_code, html_text = _fetch(url, timeout=timeout)
            text = _to_text(html_text)
            hits = _count_hits(text, keywords)
            score = sum(hits.values())
            results.append(
                SourceResult(
                    source=source_name,
                    url=url,
                    status=f"ok:{status_code}",
                    title=_extract_title(html_text),
                    score=score,
                    keyword_hits=hits,
                )
            )
        except urllib.error.HTTPError as exc:
            results.append(
                SourceResult(
                    source=source_name,
                    url=url,
                    status=f"http_error:{exc.code}",
                    title="",
                    score=0,
                    keyword_hits={k: 0 for k in keywords},
                    error=str(exc),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            results.append(
                SourceResult(
                    source=source_name,
                    url=url,
                    status="error",
                    title="",
                    score=0,
                    keyword_hits={k: 0 for k in keywords},
                    error=str(exc),
                )
            )

    results.sort(key=lambda item: item.score, reverse=True)
    return results


def write_outputs(results: list[SourceResult], keywords: list[str], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"gov_contract_scan_{stamp}.json"
    md_path = out_dir / f"gov_contract_scan_{stamp}.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords,
        "results": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Government Contract Scan",
        "",
        f"Generated: {payload['generated_at']}",
        f"Keywords: {', '.join(keywords)}",
        "",
        "| Source | Score | Status | Title |",
        "| --- | ---: | --- | --- |",
    ]
    for item in results:
        title = item.title.replace("|", " ").strip() or "(no title)"
        lines.append(f"| {item.source} | {item.score} | {item.status} | {title} |")

    lines.extend(
        [
            "",
            "## Next Actions",
            "1. Select top 3 scored sources.",
            "2. Build one-page capture packets for each lane.",
            "3. Prepare outreach drafts and schedule follow-up.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan official contracting portals for SCBE-relevant terms.")
    parser.add_argument(
        "--keywords",
        default="swarm,autonomy,navigation,ai safety,governance,interop",
        help="Comma-separated keywords used for relevance scoring.",
    )
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    parser.add_argument("--out-dir", default="artifacts/contracts", help="Output directory for JSON/MD scan results.")
    parser.add_argument(
        "--extra-url",
        action="append",
        default=[],
        help="Optional extra URL to include (repeatable).",
    )
    args = parser.parse_args()

    keywords = _parse_keywords(args.keywords)
    if not keywords:
        print("No keywords provided.")
        return 1

    results = run_scan(keywords, timeout=max(5, args.timeout), extra_urls=args.extra_url)
    json_path, md_path = write_outputs(results, keywords, out_dir=_resolve_output_dir(args.out_dir))

    print(f"Scan complete. JSON: {json_path}")
    print(f"Scan complete. MD:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

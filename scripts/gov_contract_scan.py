from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_JSON = REPO_ROOT / "references" / "federal-opportunity-sources.json"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "contracts"


@dataclass(frozen=True)
class Source:
    name: str
    type: str
    url: str
    notes: str = ""


def _strip_html(raw: str) -> str:
    # Minimal HTML stripping without external deps; good enough for keyword scoring.
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", raw)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def load_sources(path: Path) -> list[Source]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources_raw = payload.get("sources", [])
    sources: list[Source] = []
    for item in sources_raw:
        sources.append(
            Source(
                name=str(item.get("name", "")).strip(),
                type=str(item.get("type", "")).strip(),
                url=str(item.get("url", "")).strip(),
                notes=str(item.get("notes", "")).strip(),
            )
        )
    return [s for s in sources if s.name and s.url]


def score_text(text: str, keywords: list[str]) -> tuple[float, dict[str, int]]:
    lowered = text.lower()
    counts: dict[str, int] = {k: lowered.count(k) for k in keywords}
    # Log-scaled “relevance” score.
    score = float(sum(math.log1p(v) for v in counts.values()))
    return score, counts


def fetch_source(source: Source, timeout_s: int) -> dict[str, Any]:
    try:
        resp = requests.get(
            source.url,
            timeout=timeout_s,
            headers={
                "User-Agent": "SCBE-AETHERMOORE gov_contract_scan/1.0 (research; contact: issdandavis)",
            },
        )
        return {
            "ok": True,
            "status_code": resp.status_code,
            "final_url": str(resp.url),
            "text": _strip_html(resp.text),
        }
    except Exception as exc:  # pragma: no cover (network variability)
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "status_code": None,
            "final_url": source.url,
            "text": "",
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan official U.S. opportunity portals for keyword relevance.")
    parser.add_argument(
        "--keywords",
        default="swarm, autonomy, navigation, ai safety, ai governance, verification, compliance, audit, red team",
        help="Comma-separated keywords.",
    )
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory.")
    parser.add_argument("--top", type=int, default=10, help="Top-N results to print in markdown.")
    return parser.parse_args()


def write_outputs(
    out_dir: Path,
    results: list[dict[str, Any]],
    keywords: list[str],
    started_at: str,
    top_n: int,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    json_path = out_dir / f"gov_contract_scan_{stamp}.json"
    md_path = out_dir / f"gov_contract_scan_{stamp}.md"

    payload = {
        "version": "1.0",
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords,
        "sources_json": str(SOURCES_JSON),
        "top": top_n,
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Markdown brief (human-first).
    lines: list[str] = []
    lines.append("# Gov contract scan")
    lines.append("")
    lines.append(f"- started_at: {started_at}")
    lines.append(f"- completed_at: {payload['completed_at']}")
    lines.append(f"- keywords: {', '.join(keywords)}")
    lines.append("")

    ranked = sorted(results, key=lambda r: float(r.get("score", 0.0)), reverse=True)
    lines.append("## Top hits")
    lines.append("")
    for row in ranked[: max(1, int(top_n))]:
        name = str(row.get("name", "?"))
        url = str(row.get("final_url") or row.get("url") or "")
        ok = bool(row.get("ok", False))
        status_code = row.get("status_code")
        score = float(row.get("score", 0.0))
        lines.append(f"### {name}")
        lines.append(f"- ok: `{ok}`")
        lines.append(f"- status_code: `{status_code}`")
        lines.append(f"- score: `{score:.3f}`")
        lines.append(f"- url: {url}")
        lines.append("- keyword_counts:")
        counts = row.get("keyword_counts") or {}
        for k in keywords:
            lines.append(f"  - {k}: {int(counts.get(k, 0))}")
        if row.get("error"):
            lines.append(f"- error: `{row.get('error')}`")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- This is a keyword relevance scan, not a qualification gate.")
    lines.append("- Verify any opportunity on the official portal before acting.")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    args = parse_args()
    keywords = [k.strip().lower() for k in str(args.keywords).split(",") if k.strip()]
    out_dir = Path(args.out_dir)

    if not SOURCES_JSON.exists():
        print(f"[-] Missing sources file: {SOURCES_JSON}", file=sys.stderr)
        return 2

    sources = load_sources(SOURCES_JSON)
    started_at = datetime.now(timezone.utc).isoformat()

    results: list[dict[str, Any]] = []
    for source in sources:
        fetched = fetch_source(source, timeout_s=int(args.timeout))
        score, counts = score_text(fetched.get("text", ""), keywords) if fetched.get("text") else (0.0, {k: 0 for k in keywords})
        results.append(
            {
                "name": source.name,
                "type": source.type,
                "url": source.url,
                "notes": source.notes,
                "ok": fetched.get("ok", False),
                "status_code": fetched.get("status_code"),
                "final_url": fetched.get("final_url"),
                "score": score,
                "keyword_counts": counts,
                "error": fetched.get("error"),
            }
        )

    json_path, md_path = write_outputs(out_dir, results, keywords, started_at=started_at, top_n=int(args.top))

    ranked = sorted(results, key=lambda r: float(r.get("score", 0.0)), reverse=True)
    print("SCBE gov contract scan")
    print(f"json={json_path}")
    print(f"md={md_path}")
    print("top:")
    for row in ranked[: int(args.top)]:
        name = row.get("name", "?")
        score = float(row.get("score", 0.0))
        ok = row.get("ok", False)
        print(f"- {name}: score={score:.3f} ok={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

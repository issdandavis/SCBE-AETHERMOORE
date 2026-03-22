#!/usr/bin/env python3
"""
Validate that each marketing claim maps to a real local source and anchor.

Input: posts JSON
Output: claim gate report JSON
Exit code: 0 when all claims pass, 2 otherwise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lore/code claim validation gate.")
    parser.add_argument("--posts", required=True, help="Path to posts JSON")
    parser.add_argument("--repo-root", required=True, help="Repo root for source file resolution")
    parser.add_argument("--out", required=True, help="Output report JSON path")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_posts(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        maybe = payload.get("posts")
        if isinstance(maybe, list):
            return [p for p in maybe if isinstance(p, dict)]
    return []


def resolve_source(repo_root: Path, source: str) -> Path:
    src = Path(source)
    if src.is_absolute():
        return src
    return (repo_root / src).resolve()


def claim_check(repo_root: Path, claim: Dict[str, Any]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    source = str(claim.get("source", "")).strip()
    anchor = str(claim.get("anchor", "")).strip()

    if not source:
        reasons.append("missing_source")
        return False, reasons

    source_path = resolve_source(repo_root, source)
    if not source_path.exists() or not source_path.is_file():
        reasons.append(f"source_not_found:{source}")
        return False, reasons

    if not anchor:
        reasons.append("missing_anchor")
        return False, reasons

    text = source_path.read_text(encoding="utf-8", errors="ignore")
    if anchor.lower() not in text.lower():
        reasons.append(f"anchor_not_found:{anchor}")
        return False, reasons

    return True, reasons


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    posts_payload = load_json(Path(args.posts))
    posts = normalize_posts(posts_payload)

    report_rows: List[Dict[str, Any]] = []
    total_claims = 0
    failed_claims = 0

    for post in posts:
        post_id = str(post.get("id", "unknown"))
        claims = post.get("claims", [])
        if not isinstance(claims, list):
            claims = []

        for idx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            total_claims += 1
            ok, reasons = claim_check(repo_root, claim)
            if not ok:
                failed_claims += 1
            report_rows.append(
                {
                    "post_id": post_id,
                    "claim_index": idx,
                    "claim_text": str(claim.get("text", "")),
                    "source": str(claim.get("source", "")),
                    "anchor": str(claim.get("anchor", "")),
                    "pass": ok,
                    "reasons": reasons,
                }
            )

    report = {
        "summary": {
            "posts": len(posts),
            "claims_checked": total_claims,
            "claims_failed": failed_claims,
            "pass": failed_claims == 0,
        },
        "rows": report_rows,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Saved report: {out_path}")
    print(
        f"Claims checked: {total_claims} | failed: {failed_claims} | pass: {report['summary']['pass']}"
    )
    return 0 if failed_claims == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

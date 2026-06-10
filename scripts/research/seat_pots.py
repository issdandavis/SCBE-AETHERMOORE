"""Reviewer gate + build for refined pots returned by the notion-clay-to-pots workflow.

Takes the workflow's JSON result (an array of pots, each with markdown + a structured
``drift`` array + ``external_citations``) and, for every pot, enforces the publish gate
before building:

  * strip the Layer-12 phi error (the bounded wall is 1/(1+d+2*pd), no phi prefactor);
  * soften "verified" used as a quality claim to "confirmed-present";
  * guarantee a uniform ``## Claim Drift`` section synthesized from the drift array,
    inserted just before ``## References`` (so every pot carries an explicit audit trail);
  * then run build_publication to emit HTML + PDF + self-index into artifacts/publications.

Artifacts land in the gitignored build dir; nothing is published. Run:
    python -m scripts.research.seat_pots <workflow-output.json> [--version v1]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.build_publication import DEFAULT_AFFILIATION, DEFAULT_AUTHOR, build_publication  # noqa: E402

OUT_DIR = Path("artifacts/publications")
SRC_DIR = OUT_DIR / "_src"

_PHI_WALL = re.compile(r"(\(\s*1\s*\+\s*)phi\s*\*\s*(d)")
_VERIFIED_PATHS = re.compile(r"(?i)\b(?:paths\s+)?verified(\s+(?:primitive\s+)?paths?| in this repository)")
# Repo-absolute Windows paths leak from agents running print(__file__); their backslashes become
# undefined LaTeX control sequences (\symphonic, \scbe ...). Normalize to relative forward-slash form.
_WIN_REPO_PATH = re.compile(r"[A-Za-z]:\\Users\\issda\\SCBE-AETHERMOORE\\([^\s)`'\"]*)")
_VERDICT_ORDER = {"overclaim": 0, "not_found": 1, "stale": 2, "refined": 3, "matches": 4}


def _scrub(md: str) -> str:
    md = _PHI_WALL.sub(r"\1\2", md)  # 1/(1+phi*d_H+...) -> 1/(1+d_H+...)
    md = _VERIFIED_PATHS.sub("confirmed-present paths", md)
    md = _WIN_REPO_PATH.sub(lambda m: m.group(1).replace("\\", "/"), md)
    return md


def _claim_drift_section(drift: list[dict]) -> str:
    if not drift:
        return ""
    items = sorted(drift, key=lambda d: _VERDICT_ORDER.get(d.get("verdict", ""), 9))
    lines = [
        "## Claim Drift",
        "",
        "Each claim the source note made about the system, checked against the repository:",
        "",
    ]
    for d in items:
        claim = d.get("claim", "").strip().rstrip(".")
        verdict = d.get("verdict", "?")
        evidence = d.get("evidence", "").strip()
        lines.append(f"- **{verdict}** — {claim}. {evidence}")
    return "\n".join(lines) + "\n"


def _ensure_claim_drift(md: str, drift: list[dict]) -> str:
    if re.search(r"(?im)^##\s+Claim Drift\b", md):
        return md
    section = _claim_drift_section(drift)
    if not section:
        return md
    m = re.search(r"(?im)^##\s+References\b", md)
    if m:
        return md[: m.start()] + section + "\n" + md[m.start() :]
    return md.rstrip() + "\n\n" + section


def seat(pots: list[dict], *, version: str, pub_date: str, lane: str = "research") -> list[dict]:
    # Lore gets its own shelf and is not forced to carry a Claim Drift section (it is narrative,
    # not a verifiable claim); research/DF pots do. Both still get scrubbed and built.
    out_dir = OUT_DIR / "lore" if lane == "lore" else OUT_DIR
    src_dir = out_dir / "_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for pot in pots:
        slug = pot["slug"]
        md = pot["markdown"]
        if lane != "lore":
            md = _ensure_claim_drift(md, pot.get("drift", []))
        md = _scrub(md)
        src = src_dir / f"{slug}.md"
        src.write_text(md, encoding="utf-8")
        rec = build_publication(
            src,
            out_dir=out_dir,
            author=DEFAULT_AUTHOR,
            affiliation=DEFAULT_AFFILIATION,
            version=version,
            pub_date=pub_date,
        )
        reports.append(
            {
                "slug": slug,
                "lane": lane,
                "sections": rec["section_count"],
                "refs": rec["has_references"],
                "pdf": bool(rec["pdf"]),
                "drift_items": len(pot.get("drift", [])),
                "cites": len(pot.get("external_citations", [])),
                "reclassify_to": pot.get("reclassify_to"),
            }
        )
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate + build refined pots from a workflow result")
    parser.add_argument("result", type=Path, help="workflow output JSON (object with .result array, or bare array)")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--lane", default="research", choices=["research", "lore"])
    args = parser.parse_args(argv)

    data = json.loads(args.result.read_text(encoding="utf-8", errors="replace"))
    pots = data["result"] if isinstance(data, dict) else data
    reports = seat(pots, version=args.version, pub_date=args.date, lane=args.lane)
    print(json.dumps({"ok": True, "built": len(reports), "pots": reports}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

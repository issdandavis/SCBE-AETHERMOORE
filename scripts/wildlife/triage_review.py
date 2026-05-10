"""Render dispatch_results.json into a reviewable markdown report.

Reads the model replies the shepherds got back, groups them by pack and
triage decision (DELETE / DOCUMENT / FIX / OTHER), and writes a
markdown file with file:line links so the operator can scan, approve,
or veto in bulk before any mutation happens.

Usage:
    python scripts/wildlife/triage_review.py
    python scripts/wildlife/triage_review.py --in <results.json> --out <report.md>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.wildlife.packs import PACKS  # noqa: E402

DEFAULT_RESULTS = ROOT / ".scbe" / "wildlife" / "dispatch_results.json"
DEFAULT_BOARD = ROOT / ".scbe" / "wildlife" / "board.json"
DEFAULT_REPORT = ROOT / ".scbe" / "wildlife" / "triage_review.md"


def _bucket(reply: str) -> str:
    """Coarse triage bucket: which top-level decision did the model pick?"""
    r = (reply or "").strip().upper()
    if r.startswith("DELETE"):
        return "DELETE"
    if r.startswith("DOCUMENT"):
        return "DOCUMENT"
    if r.startswith("FIX"):
        return "FIX"
    return "OTHER"


def _animal_index(board: dict) -> dict[str, dict]:
    """Flatten the board so we can look up an animal by id."""
    index: dict[str, dict] = {}
    for plural, animals in board.get("packs", {}).items():
        for a in animals:
            index[a["id"]] = {"plural": plural, **a}
    return index


def render(results: dict, board: dict) -> str:
    """Build a markdown report from dispatch results + board context."""
    by_animal = _animal_index(board)
    by_pack: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, Counter] = defaultdict(Counter)
    failures: list[dict] = []
    skipped: list[dict] = []

    for r in results.get("results", []):
        if not r.get("ok"):
            if r.get("skip_reason"):
                skipped.append(r)
            else:
                failures.append(r)
            continue
        pack = r.get("pack", "?")
        bucket = _bucket(r.get("response", ""))
        ctx = by_animal.get(r.get("animal_id", ""), {})
        by_pack[pack][bucket].append({**r, "_ctx": ctx})
        counts[pack][bucket] += 1

    lines: list[str] = []
    lines.append("# Wildlife Triage Review")
    lines.append("")
    lines.append(f"**Run:** `{results.get('ran_at','?')}`  |  ")
    lines.append(f"**Total tamed:** {sum(sum(c.values()) for c in counts.values())}  |  ")
    lines.append(f"**Failures:** {len(failures)}  |  ")
    lines.append(f"**Skipped:** {len(skipped)}")
    lines.append("")

    if counts:
        lines.append("## Summary by pack")
        lines.append("")
        lines.append("| Pack | DELETE | DOCUMENT | FIX | OTHER |")
        lines.append("|---|---:|---:|---:|---:|")
        for pack in sorted(counts):
            c = counts[pack]
            lines.append(
                f"| {pack} | {c.get('DELETE',0)} | {c.get('DOCUMENT',0)} | {c.get('FIX',0)} | {c.get('OTHER',0)} |"
            )
        lines.append("")

    for pack in sorted(by_pack):
        animal = PACKS[pack].animal if pack in PACKS else pack.lower()
        plural = PACKS[pack].plural if pack in PACKS else f"{animal}s"
        lines.append(f"## {plural} ({pack})")
        lines.append("")
        for bucket in ("FIX", "DOCUMENT", "DELETE", "OTHER"):
            entries = by_pack[pack].get(bucket, [])
            if not entries:
                continue
            lines.append(f"### {bucket} — {len(entries)}")
            lines.append("")
            for e in entries:
                ctx = e.get("_ctx", {})
                path = ctx.get("path") or ""
                title = e.get("title", "")
                reply = (e.get("response", "") or "").strip().replace("\n", " ")
                if path:
                    lines.append(f"- **`{path}`** — {title[:120]}")
                else:
                    lines.append(f"- **{e.get('animal_id','?')}** — {title[:120]}")
                lines.append(f"  > {reply[:300]}")
            lines.append("")

    if failures:
        lines.append("## Failures")
        lines.append("")
        err_types: Counter = Counter()
        for f in failures:
            err_types[(f.get("error", "") or "").split(":")[0]] += 1
        for kind, n in err_types.most_common():
            lines.append(f"- `{kind}` — {n}")
        lines.append("")

    if skipped:
        lines.append("## Skipped")
        lines.append("")
        skip_types: Counter = Counter(s.get("skip_reason", "?") for s in skipped)
        for reason, n in skip_types.most_common():
            lines.append(f"- {reason} — {n}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--in", dest="in_path", default=str(DEFAULT_RESULTS))
    parser.add_argument("--board", default=str(DEFAULT_BOARD))
    parser.add_argument("--out", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        raise SystemExit(f"[triage] no results at {in_path} - run dispatch.py --execute first.")
    board_path = Path(args.board)
    if not board_path.exists():
        raise SystemExit(f"[triage] no board at {board_path}")

    results = json.loads(in_path.read_text(encoding="utf-8"))
    board = json.loads(board_path.read_text(encoding="utf-8"))
    md = render(results, board)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"[triage] report written -> {out_path}")
    print(f"  {len(results.get('results', []))} animals processed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""claim_evidence_crosswalk: turn the research-claim registry from green-by-fiat prose into a gate.

Every status=verified claim in config/eval/aether_research_claim_registry.v1.json carries a repo_action
(prose). Nothing enforced that the action maps to anything real, so a "verified" claim could imply repo
coverage that does not exist. This crosswalk asserts each verified claim's `evidence` is either backed by
a real on-disk path (kind file/test/script that resolves) or HONESTLY fenced as kind=backlog -- the same
"claim -> evidence or an explicit backlog" discipline the registry itself preaches. CI-checkable, offline.

    python scripts/eval/claim_evidence_crosswalk.py          # human table, exits 1 if any claim is unbacked
    python scripts/eval/claim_evidence_crosswalk.py --json   # machine-readable rows
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "config" / "eval" / "aether_research_claim_registry.v1.json"
_PATH_KINDS = {"file", "test", "script"}


def crosswalk(registry: Dict[str, Any], repo_root: Path) -> List[Dict[str, Any]]:
    """One row per verified claim that carries a repo_action: does its evidence resolve, or is it an
    honest backlog fence? `ok=False` means a verified claim asserts coverage it cannot back."""
    rows: List[Dict[str, Any]] = []
    for c in registry.get("claims", []):
        if c.get("status") != "verified" or not c.get("repo_action"):
            continue
        cid = c.get("claim_id")
        ev = c.get("evidence")
        if not isinstance(ev, dict) or "kind" not in ev:
            rows.append({"claim_id": cid, "ok": False, "evidence_status": "missing", "detail": "no evidence field"})
            continue
        kind = ev["kind"]
        if kind == "backlog":
            rows.append({"claim_id": cid, "ok": True, "evidence_status": "backlog", "detail": ev.get("note", "")})
        elif kind in _PATH_KINDS:
            path = ev.get("path", "")
            exists = bool(path) and (repo_root / path).exists()
            rows.append(
                {
                    "claim_id": cid,
                    "ok": exists,
                    "evidence_status": "resolved" if exists else "broken_path",
                    "detail": path,
                }
            )
        else:
            rows.append({"claim_id": cid, "ok": False, "evidence_status": "bad_kind", "detail": str(kind)})
    return rows


def check(registry: Dict[str, Any], repo_root: Path) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows = crosswalk(registry, repo_root)
    problems = [r for r in rows if not r["ok"]]
    return (not problems), rows, problems


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="claim-evidence-crosswalk", description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable rows")
    a = ap.parse_args(argv)
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    ok, rows, problems = check(registry, REPO_ROOT)
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            mark = "ok  " if r["ok"] else "FAIL"
            print("  [%s] %-38s %-12s %s" % (mark, r["claim_id"], r["evidence_status"], str(r["detail"])[:60]))
    if not ok:
        print(
            "FAIL: %d verified claim(s) assert coverage without resolvable evidence or a backlog fence" % len(problems)
        )
        return 1
    print("OK: %d verified claims all crosswalk to real evidence or an honest backlog fence" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

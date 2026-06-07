"""Route the corridor router through the canonical bijection gate.

The corridor atlas ROUTES goal -> chosen_corridor. The stated goal of the program is
BIJECTIVE alignment: each known goal should map one-to-one to its correct corridor. This
script feeds the router's actual picks into src/governance/bijection_gate.py and asks, per
stratum: is the router a usable one-to-one router, or only count-correct?

It reuses the existing fixtures (overlap-INDEPENDENT ground truth) from
scripts/eval/corridor_ranker_baseline.py so nothing is forked. Each goal gets ONE canonical
page with the correct corridor placed FIRST (favorable to the router); if it still routes to
the high-overlap distractor, the bijection failure is robust.

Run:
    python scripts/eval/corridor_bijection_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.eval.corridor_ranker_baseline import (  # noqa: E402
    _EASY,
    _FILLER_LINKS,
    _HELDOUT_SYNONYMS,
    _LOW_OVERLAP,
    _SAFETY,
    _build,
    _link,
    full_ranker_pick,
)
from src.governance.bijection_gate import audit_bijection  # noqa: E402

NO_PICK = "<NO_PICK>"


def _fillers(k: int, avoid: set[str]) -> list[dict[str, Any]]:
    out = []
    for text, href in _FILLER_LINKS:
        if text in avoid:
            continue
        out.append(_link(text, href))
        if len(out) == k:
            break
    return out


def _maps_for(stratum: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return (truth: goal->correct, candidate: goal->router pick) for one stratum.

    Correct corridor is placed FIRST in DOM order (favorable); a high-overlap distractor (when
    the stratum has one) follows, then neutral fillers.
    """
    truth: dict[str, str] = {}
    candidate: dict[str, str] = {}

    if stratum == "easy_overlap":
        rows = [(g, ct, ch, None, None) for (g, ct, ch) in _EASY]
    elif stratum == "low_overlap_correct":
        rows = list(_LOW_OVERLAP)
    elif stratum == "heldout_synonym":
        rows = list(_HELDOUT_SYNONYMS)
    elif stratum == "safety_override":
        # correct = the SAFE alternative; the "distractor" is the high-risk goal-keyword corridor.
        rows = [(g, safe, sh, risky, rh) for (g, risky, rh, safe, sh) in _SAFETY]
    else:
        raise ValueError(stratum)

    for goal, ctext, chref, dtext, dhref in rows:
        avoid = {ctext} | ({dtext} if dtext else set())
        links = [_link(ctext, chref)]  # correct FIRST
        if dtext:
            links.append(_link(dtext, dhref))
        links += _fillers(2, avoid)
        page = {"goal": goal, "links": links, "buttons": [], "tabs": []}
        payload = _build(page, goal)
        truth[goal] = ctext
        candidate[goal] = full_ranker_pick(payload) or NO_PICK
    return truth, candidate


def main() -> int:
    strata = [
        "easy_overlap",
        "low_overlap_correct",
        "heldout_synonym",
        "safety_override",
    ]
    print("\n=== corridor router :: bijection gate (goal -> correct corridor) ===")
    print(
        "router is usable as a one-to-one router ONLY where verdict = BIJECTIVE_USE\n"
    )
    print(
        f"{'stratum':<22} {'verdict':<26} {'matched':>8} {'wrong':>6} {'ghost':>6} {'dup':>4}"
    )
    overall_usable = True
    for stratum in strata:
        truth, candidate = _maps_for(stratum)
        audit = audit_bijection(truth, candidate)
        n = len(truth)
        print(
            f"{stratum:<22} {audit.verdict:<26} {audit.matched_count:>3}/{n:<4} "
            f"{len(audit.wrong_matches):>6} {len(audit.target_ghosts):>6} {len(audit.duplicate_targets):>4}"
        )
        if not audit.is_bijective:
            overall_usable = False

    print("\n--- detail: where it fails, and to what it mis-routes ---")
    for stratum in ["low_overlap_correct", "heldout_synonym"]:
        truth, candidate = _maps_for(stratum)
        audit = audit_bijection(truth, candidate)
        for wm in audit.wrong_matches:
            print(
                f"  [{stratum}] goal-correct '{wm.expected_target}'  ->  router chose '{wm.predicted_target}'"
            )

    print(
        "\nVERDICT: "
        + (
            "router is a bijective one-to-one router on ALL strata."
            if overall_usable
            else "router is NOT bijective -- usable only on the strata marked BIJECTIVE_USE. "
            "On synonym targeting it routes the goal keyword's HIGH-overlap distractor, not the "
            "semantically-correct corridor: count-shaped routing, not identity-preserving. Use the "
            "hard low-risk pre-filter for safety, but do NOT treat the score as a one-to-one router."
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

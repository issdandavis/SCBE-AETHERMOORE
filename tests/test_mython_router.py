#!/usr/bin/env python3
"""Eval + regression gate for the mython shell router (scripts/mython_bridge.py).

This is the brain behind the interactive `scbe shell`'s plain-English routing:
free text -> find_cell() picks a GRID cell -> the shell AUTO-ACTS when the
derived confidence is >= 0.5 (no confirmation). So a router that fires the wrong
cell at >=0.5 silently runs the wrong command.

The baseline scorer is a raw substring trigger-count: confidence = score/(score+1),
so ANY single keyword match (score~1) lands at ~0.5 and auto-acts. Two failure
modes follow directly:
  * substring false positives  -- "design" contains "sign" -> geoseal/seal
  * shared-keyword overload     -- "route" is in 2 cells, "verify/check/validate"
                                   collide, so an ambiguous one-word hit auto-acts.

Cases are written in USER VOICE (not pattern words). A ~60/40 tune/holdout split
guards against tuning the scorer to the test: the scorer change must lift the
holdout too, not just the cases used while iterating.

Metrics (decision-level, per the corridor-ranker lesson -- score deltas are
decorative, the chosen cell and the auto-act decision are what matter):
  * positive routing accuracy  -- right (category, operation) chosen
  * decoy auto-act rate        -- fraction of out-of-scope inputs that reach the
                                  >=0.5 auto-act floor (want 0: they should fall
                                  through to the LLM / clarify path instead)

Run as a report:   python tests/test_mython_router.py
Run as a gate:      pytest tests/test_mython_router.py -v
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import mython_bridge as mb  # noqa: E402

AUTO_ACT_FLOOR = 0.5  # scbe.js shell auto-acts on a mython result at conf >= 0.5


# ── Labeled corpus (user voice, not trigger words) ──────────────────────────
# kind: "pos" expects (cat, op); "decoy" expects no auto-act (out of scope or
#       a real word used conversationally, not as a command).
# split: "tune" cases may inform the scorer design; "hold" cases are not looked
#       at while iterating -- they prove generalization.
CASES = [
    # --- positives: clear commands -----------------------------------------
    ("compile my goal into a plan", "pos", ("geoseal", "compile"), "tune"),
    ("seal this artifact and sign it", "pos", ("geoseal", "seal"), "tune"),
    ("verify the workspace integrity", "pos", ("geoseal", "verify"), "tune"),
    ("scan the repo for threats", "pos", ("governance", "scan"), "tune"),
    ("route this task through the compass", "pos", ("governance", "route"), "tune"),
    ("encode this phrase in the RU tongue", "pos", ("tongues", "encode"), "tune"),
    ("search arxiv for hyperbolic geometry papers", "pos", ("research", "arxiv"), "tune"),
    ("find github repos about reservoir computing", "pos", ("research", "github"), "tune"),
    ("look up huggingface models for embeddings", "pos", ("research", "hf-models"), "tune"),
    ("run a multi-agent flow for this task", "pos", ("governance", "flow"), "hold"),
    ("stamp this receipt", "pos", ("geoseal", "seal"), "hold"),
    ("pull preprints on prime gaps", "pos", ("research", "arxiv"), "hold"),
    # --- decoys: must NOT auto-act (conf < 0.5) -----------------------------
    ("hello there how are you", "decoy", None, "tune"),
    ("tell me a joke", "decoy", None, "tune"),
    ("explain this repo to me", "decoy", None, "tune"),  # "explain" overloads explain-route
    ("I think the design looks great", "decoy", None, "tune"),  # "design" contains "sign"
    ("let's plan our trip this weekend", "decoy", None, "tune"),  # "plan" -> compile
    ("can you help me model the universe", "decoy", None, "hold"),  # "model" -> hf-models
    ("just checking in on you", "decoy", None, "hold"),  # "checking" contains "check"
    ("good morning everyone", "decoy", None, "hold"),
    ("route sixty six is a famous highway", "decoy", None, "hold"),  # "route" in 2 cells
    ("what is the meaning of life", "decoy", None, "hold"),
]


def route(text: str):
    """Return (cat, op, confidence) using the live scorer, no subprocess.

    Uses the module's own confidence derivation when present (margin-aware),
    else the legacy score/(score+1). find_cell() is pure (no command runs).
    """
    cell = mb.find_cell(text)
    if not cell:
        return (None, None, 0.0)
    cat, op, _cmd, _takes, score = cell
    if hasattr(mb, "confidence_for"):
        conf = mb.confidence_for(text)
    else:
        conf = round(score / (score + 1), 4)
    return (cat, op, conf)


def _report(rows):
    pos = [c for c in rows if c[1] == "pos"]
    decoy = [c for c in rows if c[1] == "decoy"]
    pos_hit = 0
    pos_autoact = 0
    for text, _kind, expect, _split in pos:
        cat, op, conf = route(text)
        if (cat, op) == expect:
            pos_hit += 1
            if conf >= AUTO_ACT_FLOOR:
                pos_autoact += 1
    decoy_autoact = 0
    for text, _kind, _expect, _split in decoy:
        _cat, _op, conf = route(text)
        if conf >= AUTO_ACT_FLOOR:
            decoy_autoact += 1
    return {
        "positives": len(pos),
        "pos_routed_right": pos_hit,
        "pos_autoact_right": pos_autoact,
        "decoys": len(decoy),
        "decoy_autoact_BAD": decoy_autoact,
    }


# ── Gate (asserts the FIXED behavior; baseline numbers are in the report) ───
def test_positives_route_to_the_right_cell():
    """Every clear command picks its intended (category, operation)."""
    misses = []
    for text, kind, expect, _split in CASES:
        if kind != "pos":
            continue
        cat, op, _conf = route(text)
        if (cat, op) != expect:
            misses.append((text, (cat, op), expect))
    assert not misses, f"mis-routed positives: {misses}"


def test_clear_positives_reach_auto_act():
    """A clear command should be confident enough to act on (conf >= floor)."""
    weak = []
    for text, kind, expect, _split in CASES:
        if kind != "pos":
            continue
        cat, op, conf = route(text)
        if (cat, op) == expect and conf < AUTO_ACT_FLOOR:
            weak.append((text, conf))
    # Allow a small number of genuinely terse positives to stay below the floor,
    # but the bulk must be actionable.
    assert len(weak) <= 2, f"too many positives below auto-act floor: {weak}"


def test_decoys_do_not_auto_act():
    """Out-of-scope / conversational input must stay below the auto-act floor.

    This is the null gate: the scorer must not silently fire a command on a
    substring false positive or a single shared keyword.
    """
    fired = []
    for text, kind, _expect, _split in CASES:
        if kind != "decoy":
            continue
        cat, op, conf = route(text)
        if conf >= AUTO_ACT_FLOOR:
            fired.append((text, (cat, op), conf))
    assert not fired, f"decoys auto-acted (false fire): {fired}"


def test_holdout_generalizes():
    """Holdout cases (not used while tuning) meet the same bar."""
    hold = [c for c in CASES if c[3] == "hold"]
    rep = _report(hold)
    assert rep["decoy_autoact_BAD"] == 0, f"holdout decoys fired: {rep}"
    assert rep["pos_routed_right"] >= max(1, rep["positives"] - 1), f"holdout routing weak: {rep}"


if __name__ == "__main__":
    full = _report(CASES)
    tune = _report([c for c in CASES if c[3] == "tune"])
    hold = _report([c for c in CASES if c[3] == "hold"])
    has_fix = hasattr(mb, "confidence_for")
    print(f"mython router eval  ({'FIXED scorer' if has_fix else 'BASELINE scorer'})")
    print(f"  auto-act floor = {AUTO_ACT_FLOOR}")
    for name, rep in (("ALL", full), ("tune", tune), ("hold", hold)):
        print(
            f"  [{name:>4}] positives routed {rep['pos_routed_right']}/{rep['positives']}"
            f"  auto-act-right {rep['pos_autoact_right']}/{rep['positives']}"
            f"  | decoys fired (BAD) {rep['decoy_autoact_BAD']}/{rep['decoys']}"
        )
    print()
    print("  per-case:")
    for text, kind, expect, split in CASES:
        cat, op, conf = route(text)
        flag = ""
        if kind == "decoy" and conf >= AUTO_ACT_FLOOR:
            flag = "  <- FALSE FIRE"
        elif kind == "pos" and (cat, op) != expect:
            flag = "  <- MIS-ROUTE"
        cell_label = f"{cat}/{op}" if cat else "(no match)"
        print(f"    [{split}] {kind:5} conf={conf:.3f}  {cell_label:<28} <- {text!r}{flag}")

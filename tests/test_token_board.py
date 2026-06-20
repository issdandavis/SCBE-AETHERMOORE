"""token_board: conlang tokens bound to verified moves, scored under escalating governance.

Proves the math is the truth (not a fuzzy matcher), the harness is sound (reference oracle = 100%
everywhere), pruning removes only provably-illegal moves, and a None pick never counts as a pass.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import token_board as tb  # noqa: E402


def test_truth_is_the_math():
    assert tb._truth(1) == "unit"
    assert tb._truth(7) == "prime" and tb._truth(29) == "prime"
    assert tb._truth(8) == "prime-power" and tb._truth(49) == "prime-power"
    assert tb._truth(12) == "composite" and tb._truth(91) == "composite"


def test_reference_oracle_clears_every_condition():
    # the harness validation, as a test: a correct chooser must score 100% on ALL conditions,
    # so any sub-100% under a real model is the model, not a broken board
    res = tb.run_board(tb.DEFAULT_NUMBERS, tb.reference_ask)
    assert all(res[name]["acc"] == 1.0 for name in tb.CONDITIONS)


def test_parse_token_is_exact_not_fuzzy():
    # the measurement guard: exactly one legal token, or no move
    assert tb._parse_token("ZOR", ["UNE", "ZOR", "KAEL", "VEX"]) == "ZOR"
    assert tb._parse_token("i think ZOR", ["UNE", "ZOR", "KAEL", "VEX"]) == "ZOR"
    assert tb._parse_token("ZOR or VEX", ["UNE", "ZOR", "KAEL", "VEX"]) is None  # ambiguous -> no move
    assert tb._parse_token("prime", ["UNE", "ZOR", "KAEL", "VEX"]) is None  # not a token -> no move


def test_pruning_removes_only_provably_illegal_moves():
    # a chooser that guesses wrong (prime) before right (composite) on 91: pruning the false token
    # lets it land; the answer is never revealed, only the illegal move removed
    picks = iter(["ZOR", "VEX"])  # ZOR=prime (false for 91) then VEX=composite (true)

    def chooser(prompt):
        return next(picks)

    assert tb.pruned_pick(91, chooser) == "composite"
    # board (no pruning) with the same first wrong pick just fails
    assert tb.board_pick(91, lambda p: "ZOR") == "prime" != tb._truth(91)


def test_none_pick_counts_as_wrong_never_a_pass():
    res = tb.run_board([7, 12], lambda p: "")  # empty replies -> no parsable move
    assert res["raw"]["correct"] == 0 and res["board"]["correct"] == 0


def test_tool_is_always_correct():
    assert all(tb.tool_label(n) == tb._truth(n) for n in tb.DEFAULT_NUMBERS)

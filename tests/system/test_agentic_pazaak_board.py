from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "agentic_pazaak_board.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_agentic_pazaak_board_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bitboards_encode_lane_flags() -> None:
    module = load_module()
    lanes = [
        module.TaskLane("clean", value=2, risk=1, verified=True),
        module.TaskLane("risky", value=5, risk=4, verified=False, conflict=True),
    ]

    boards = module.bitboards(lanes)

    assert boards["high_value"] == 0b10
    assert boards["high_risk"] == 0b10
    assert boards["unverified"] == 0b10
    assert boards["conflict"] == 0b10


def test_stand_hold_is_negative_zero_quarantine_move() -> None:
    module = load_module()
    card = next(card for card in module.load_cards() if card.card_id == "stand_hold")
    lane = module.TaskLane("uncertain", value=3, risk=4, verified=False)

    after = module.apply_card(lane, card)

    assert card.symbol == "-0"
    assert after.blocked is True
    assert after.risk == 3


def test_recommend_moves_prefers_verifier_for_high_risk_unverified_lane() -> None:
    module = load_module()
    cards = module.load_cards()
    lanes = [module.TaskLane("verification", value=5, risk=4, verified=False)]

    moves = module.recommend_moves(lanes, cards, limit=3)

    assert moves[0].card_id == "verify_minus_risk"
    assert moves[0].after["verified"] is True
    assert moves[0].after["risk"] == 1


def test_recommend_moves_prefers_claim_territory_for_conflict_lane() -> None:
    module = load_module()
    cards = module.load_cards()
    lanes = [module.TaskLane("integration", value=5, risk=3, verified=False, conflict=True)]

    moves = module.recommend_moves(lanes, cards, limit=3)

    assert any(move.card_id == "claim_territory" for move in moves)

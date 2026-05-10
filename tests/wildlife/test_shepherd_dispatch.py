"""Pin shepherd model selection + dispatch plan structure.

These tests lock the cost/safety contract:
- DRAGONS must never be auto-dispatched (require human rider)
- HORSES must never be auto-dispatched (training pipeline owns them)
- SHEEP and CROWS must use cheapest backend (Ollama local)
- Every dispatchable pack must have a non-empty prompt template
- Plan must surface skip_reason for non-dispatchable packs so the operator
  is never confused about why something didn't run
"""

from __future__ import annotations

from scripts.wildlife.dispatch import build_plan
from scripts.wildlife.shepherds import (
    SHEPHERDS,
    is_auto_dispatchable,
    render_prompt,
    shepherd_for,
)

# ----------------------------- shepherd registry -------------------------- #


def test_every_pack_has_a_shepherd() -> None:
    expected = {"WOLF", "CROW", "GOAT", "BEE", "CAT", "HORSE", "SHEEP", "OTTER", "DRAGON"}
    assert set(SHEPHERDS.keys()) == expected


def test_dragons_are_human_only_never_auto() -> None:
    s = shepherd_for("DRAGON")
    assert s.backend == "human-only"
    assert is_auto_dispatchable("DRAGON") is False
    # Prompt must be a sentinel, not a real prompt
    assert render_prompt("DRAGON", "DARPA proposal") is None


def test_horses_are_pipeline_owned_never_auto() -> None:
    s = shepherd_for("HORSE")
    assert s.backend == "training-pipeline"
    assert is_auto_dispatchable("HORSE") is False
    assert render_prompt("HORSE", "v6h training run") is None


def test_sheep_and_crows_use_cheapest_backend() -> None:
    """Bulk trivial work must not hit paid HF."""
    for pack in ("SHEEP", "CROW"):
        s = shepherd_for(pack)
        assert s.backend == "ollama", f"{pack} must use ollama (cheapest)"
        assert s.cost_tier == "free", f"{pack} must be free tier"


def test_wolves_use_a_real_model_not_local() -> None:
    """Critical bugs deserve more capable model than 1.5B."""
    s = shepherd_for("WOLF")
    # Either local 7B+ or HF — never the 1.5B coder used for sheep
    assert "1.5b" not in s.model.lower(), "WOLF shepherd must not be 1.5B model"


def test_every_dispatchable_pack_has_nonempty_prompt() -> None:
    for pack_name, shepherd in SHEPHERDS.items():
        if shepherd.backend in {"ollama", "huggingface"}:
            prompt = render_prompt(pack_name, "sample title")
            assert prompt is not None, f"{pack_name} dispatchable but prompt is None"
            assert "sample title" in prompt, f"{pack_name} prompt template missing {{title}}"
            assert len(prompt) > 30, f"{pack_name} prompt too short ({len(prompt)})"


def test_unknown_pack_has_no_shepherd() -> None:
    assert shepherd_for("HIPPO") is None
    assert is_auto_dispatchable("HIPPO") is False
    assert render_prompt("HIPPO", "anything") is None


# ----------------------------- dispatch plan ------------------------------ #


def _mini_board(packs_with_counts: dict[str, int]) -> dict:
    from scripts.wildlife.packs import PACKS

    packs_section = {}
    for pack_name, count in packs_with_counts.items():
        plural = PACKS[pack_name].plural
        packs_section[plural] = [
            {"id": f"{pack_name.lower()}-{i}", "title": f"thing {i}", "liberties": 3} for i in range(count)
        ]
    return {
        "schema": "wildlife-board-v1",
        "harvested_at": "2026-05-09T00:00:00Z",
        "packs": packs_section,
    }


def test_plan_marks_dragons_as_human_only_with_reason() -> None:
    board = _mini_board({"DRAGON": 2, "WOLF": 3})
    plan = build_plan(board, max_per_pack=5)
    dragons_entry = plan["by_pack"]["dragons"]
    assert dragons_entry["auto_dispatchable"] is False
    assert "human" in dragons_entry["skip_reason"].lower()
    # Dragons should NOT count toward auto-dispatchable totals
    assert plan["totals"]["auto_dispatchable"] == 3  # only the wolves


def test_plan_marks_horses_as_pipeline_owned_with_reason() -> None:
    board = _mini_board({"HORSE": 4})
    plan = build_plan(board, max_per_pack=5)
    horses_entry = plan["by_pack"]["horses"]
    assert horses_entry["auto_dispatchable"] is False
    assert "training" in horses_entry["skip_reason"].lower()


def test_plan_caps_per_pack_at_max_per_pack() -> None:
    """A pack with 50 animals shouldn't try to dispatch all 50."""
    board = _mini_board({"CROW": 50})
    plan = build_plan(board, max_per_pack=3)
    assert plan["by_pack"]["crows"]["count_total"] == 50
    assert plan["by_pack"]["crows"]["count_planned"] == 3
    assert len(plan["by_pack"]["crows"]["preview"]) == 3


def test_plan_skips_empty_packs() -> None:
    board = _mini_board({"CROW": 2})
    plan = build_plan(board, max_per_pack=5)
    # Wolves not in board → not in plan
    assert "wolves" not in plan["by_pack"]
    assert "crows" in plan["by_pack"]


def test_plan_includes_cost_tier_for_each_dispatchable_pack() -> None:
    """Operator can see at-a-glance whether a pack uses free or paid backend."""
    board = _mini_board({"SHEEP": 3, "WOLF": 2})
    plan = build_plan(board, max_per_pack=5)
    assert plan["by_pack"]["sheep"]["shepherd"]["cost_tier"] == "free"
    assert plan["by_pack"]["wolves"]["shepherd"]["cost_tier"] in {"cheap", "standard", "expensive"}

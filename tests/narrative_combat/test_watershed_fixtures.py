from __future__ import annotations

from src.narrative_combat.director import Director
from src.narrative_combat.go_board.director import GoDirector
from src.narrative_combat.watershed_fixtures import (
    watershed_ruin_group_board,
    yun_zhou_yu_ping_corridor,
)


def test_watershed_corridor_fixture_preserves_yun_zhou_not_secretly_stronger():
    encounter = yun_zhou_yu_ping_corridor(seed=20260524)
    yun_zhou, yu_ping = encounter.fighters

    assert yun_zhou.stats["qi"] < yu_ping.stats["qi"]
    assert "shi_gan_read" in yun_zhou.concealed
    assert encounter.objective == "stabilize"
    assert "the rotten sub-floor cannot take sudden heat" in encounter.terrain.constraints


def test_watershed_corridor_runs_through_existing_director():
    fight = Director(yun_zhou_yu_ping_corridor(seed=20260524)).run()

    assert fight["schema"] == "scbe.narrative_combat.fight.v1"
    assert fight["encounter_id"] == "watershed_yun_zhou_yu_ping_corridor"
    assert fight["planned_goal"]["winner"] == "Pei Yun Zhou"
    assert fight["beats"]
    assert any("shi_gan_read" in beat["state_shift"].get("revealed", []) for beat in fight["beats"])
    assert "qi backlash" not in fight["aftermath"]["price_paid"]
    assert any("exposed before anyone can name it" in fact for fact in fight["aftermath"]["continuity_facts"])


def test_watershed_group_board_runs_through_go_director():
    fight = GoDirector(watershed_ruin_group_board(seed=20260524)).run()

    assert fight["schema"] == "scbe.narrative_combat.go_fight.v1"
    assert fight["encounter_id"] == "watershed_ruin_group_board"
    assert fight["terrain"]["name"] == "outer Watershed hall"
    assert any(turn["board_event"] == "qi_claimed" for turn in fight["turns"])

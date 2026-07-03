from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_worktree_garden():
    path = Path(__file__).resolve().parents[2] / "scripts" / "system" / "worktree_garden.py"
    spec = importlib.util.spec_from_file_location("worktree_garden", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def make_config(tmp_path: Path, *, max_plots: int = 3) -> dict:
    house = tmp_path / "house"
    storage = tmp_path / "storage"
    house.mkdir()
    storage.mkdir()
    return {
        "schema": "scbe_worktree_garden_config_v1",
        "garden_name": "Test Garden",
        "max_plots": max_plots,
        "default_lease_hours": 1,
        "zones": {
            "house": {"label": "House", "max_plots": 1, "purpose": "primary"},
            "outsource_storage": {"label": "Outsource", "max_plots": 2, "purpose": "storage"},
        },
        "plot_seeds": [
            {
                "id": "house-test",
                "zone": "house",
                "kind": "git",
                "path": str(house),
                "role": "primary",
                "max_agents": 1,
            },
            {
                "id": "storage-test",
                "zone": "outsource_storage",
                "kind": "storage",
                "path": str(storage),
                "role": "storage",
                "max_agents": 1,
            },
        ],
    }


def test_build_state_tracks_capacity_and_plots(tmp_path: Path):
    wg = load_worktree_garden()
    state = wg.build_state(make_config(tmp_path, max_plots=1), {})

    assert state["summary"]["plots"] == 2
    assert state["summary"]["over_plot_capacity"] is True
    assert {plot["id"] for plot in state["plots"]} == {"house-test", "storage-test"}


def test_attach_and_release_agent_lease(tmp_path: Path):
    wg = load_worktree_garden()
    config = make_config(tmp_path)
    state = wg.build_state(config, {})

    attached = wg.attach_agent(
        config,
        state,
        argparse.Namespace(agent="codex", plot="house-test", task="tend test plot", mode="work", ttl_hours=1),
    )
    house = next(plot for plot in attached["plots"] if plot["id"] == "house-test")

    assert attached["summary"]["active_leases"] == 1
    assert house["active_agents"] == 1
    assert house["health"] == "occupied"

    released = wg.release_agent(
        config,
        attached,
        argparse.Namespace(agent="codex", plot="house-test", lease_id=""),
    )

    assert released["summary"]["active_leases"] == 0
    assert released["released"][0]["agent"] == "codex"


def test_missing_plot_is_marked_missing(tmp_path: Path):
    wg = load_worktree_garden()
    config = make_config(tmp_path)
    config["plot_seeds"].append(
        {
            "id": "missing-test",
            "zone": "outsource_storage",
            "kind": "storage",
            "path": str(tmp_path / "does-not-exist"),
            "role": "missing",
            "max_agents": 1,
        }
    )

    state = wg.build_state(config, {})
    missing = next(plot for plot in state["plots"] if plot["id"] == "missing-test")

    assert missing["health"] == "missing"
    assert state["summary"]["missing_plots"] == 1

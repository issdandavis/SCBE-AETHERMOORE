from __future__ import annotations

import json
from pathlib import Path

from scripts import list_obsidian_vaults as vaults


def test_active_vault_path_prefers_open_flag(tmp_path: Path) -> None:
    config_path = tmp_path / "obsidian.json"
    config_path.write_text(
        json.dumps(
            {
                "vaults": {
                    "a": {"path": str(tmp_path / "Closed"), "ts": 1000, "open": False},
                    "b": {"path": str(tmp_path / "Open"), "ts": 500, "open": True},
                }
            }
        ),
        encoding="utf-8",
    )

    active = vaults.active_vault_path(config_path)

    assert active == tmp_path / "Open"

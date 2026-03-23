from __future__ import annotations

import json

from scripts.system.storage_interaction_mesh_lab import main


def test_storage_interaction_mesh_lab_writes_artifact(tmp_path) -> None:
    out_path = tmp_path / "mesh.json"

    rc = main(
        [
            "--max-notes",
            "6",
            "--output-json",
            str(out_path),
        ]
    )

    assert rc == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["experiment"] == "storage_interaction_mesh"
    assert payload["note_count"] == 6
    assert payload["mesh"]["stats"]["record_count"] == 6

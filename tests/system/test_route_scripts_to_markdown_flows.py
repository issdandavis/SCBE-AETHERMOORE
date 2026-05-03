from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.system.route_scripts_to_markdown_flows import build_routes


SCRIPT_PATTERN = "scripts/system/build_coding_decks.py"


def test_build_routes_writes_dr_markdown_cards_with_script_route_metadata(tmp_path: Path) -> None:
    manifest = build_routes([SCRIPT_PATTERN], tmp_path)

    assert manifest["schema_version"] == "scbe_script_markdown_flow_manifest_v1"
    assert manifest["card_tongue"] == "DR"
    assert manifest["card_tongue_name"] == "Draumric"
    assert manifest["card_language"] == "Markdown"
    assert manifest["tongue_full_names"]["KO"] == "Kor'aelin"
    assert manifest["card_count"] == 1
    assert sum(manifest["by_script_tongue"].values()) == 1

    card = manifest["cards"][0]
    assert card["script_path"] == SCRIPT_PATTERN
    assert card["card_tongue"] == "DR"
    assert card["card_tongue_name"] == "Draumric"
    assert card["card_language"] == "Markdown"
    assert card["script_tongue"] in {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert card["script_tongue_name"]
    assert card["script_language"]
    assert card["source_sha256"]

    card_path = Path(card["card_path"])
    assert card_path.exists()
    body = card_path.read_text(encoding="utf-8")
    assert 'schema_version: "scbe_script_markdown_flow_v1"' in body
    assert 'card_language: "Markdown"' in body
    assert 'card_tongue_name: "Draumric"' in body
    assert "Card tongue: `DR` (Draumric)" in body
    assert "Script tongue: `" in body
    assert "## Agentic Use" in body
    assert f"python {SCRIPT_PATTERN}" in body


def test_build_routes_manifest_and_index_are_stable(tmp_path: Path) -> None:
    first = build_routes([SCRIPT_PATTERN], tmp_path)
    second = build_routes([SCRIPT_PATTERN], tmp_path)

    assert first == second
    assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == json.dumps(
        second, indent=2, sort_keys=True, ensure_ascii=True
    ) + "\n"
    index = (tmp_path / "_index.md").read_text(encoding="utf-8")
    assert "Card tongue: `DR` (Draumric)" in index
    assert "Card language: `Markdown`" in index
    assert "`KO` = Kor'aelin" in index
    assert "`DR` = Draumric" in index


def test_cli_emits_json_manifest_to_custom_output(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/system/route_scripts_to_markdown_flows.py",
            "--pattern",
            SCRIPT_PATTERN,
            "--out",
            str(tmp_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(result.stdout)
    assert manifest["card_count"] == 1
    assert manifest["card_tongue"] == "DR"
    assert manifest["card_tongue_name"] == "Draumric"
    assert manifest["cards"][0]["script_path"] == SCRIPT_PATTERN

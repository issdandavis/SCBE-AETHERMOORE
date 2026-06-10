from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "build_model_portfolio_board.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_model_portfolio_board", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classifies_merge_outputs_and_inputs_from_local_profiles() -> None:
    module = _load_module()
    board = module.build_portfolio(
        [
            {
                "repo_id": "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v2",
                "author": "issdandavis",
                "downloads": 0,
                "likes": 0,
                "pipeline_tag": "",
                "tags": [],
                "last_modified": "",
            },
            {
                "repo_id": "issdandavis/scbe-coding-agent-qwen-ca-geoseal-smoke-repair-v1",
                "author": "issdandavis",
                "downloads": 0,
                "likes": 0,
                "pipeline_tag": "",
                "tags": [],
                "last_modified": "",
            },
        ]
    )

    by_repo = {row["repo_id"]: row for row in board["models"]}
    assert by_repo["issdandavis/scbe-coding-agent-qwen-merged-coding-model-v2"]["bucket"] == "merge_candidate"
    assert (
        by_repo["issdandavis/scbe-coding-agent-qwen-ca-geoseal-smoke-repair-v1"]["bucket"]
        == "active_specialist_adapter"
    )
    assert board["policy"]["do_not_merge_all"] is True


def test_classifies_org_namespace_as_mirror_check() -> None:
    module = _load_module()
    board = module.build_portfolio(
        [
            {
                "repo_id": "SCBE-AETHER/phdm-21d-embedding",
                "author": "SCBE-AETHER",
                "downloads": 0,
                "likes": 0,
                "pipeline_tag": "",
                "tags": [],
                "last_modified": "",
            }
        ]
    )

    row = board["models"][0]
    assert row["bucket"] == "foundational_reference"
    assert row["recommended_action"] == "mirror_check_keep_one_canonical_owner_or_mark_as_org_mirror"


def test_write_outputs_creates_json_and_markdown(tmp_path: Path) -> None:
    module = _load_module()
    board = module.build_portfolio([])

    paths = module.write_outputs(board, tmp_path)

    assert Path(paths["json"]).exists()
    assert Path(paths["markdown"]).exists()
    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scbe_model_portfolio_board_v1"

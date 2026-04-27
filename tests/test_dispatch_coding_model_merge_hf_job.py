from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "dispatch_coding_model_merge_hf_job.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("test_dispatch_coding_model_merge_hf_job_module", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_profile_normalizes_weights() -> None:
    module = _load_module()
    profile = {
        "schema_version": "scbe_coding_model_merge_profile_v1",
        "merge_id": "merge",
        "base_model": "base",
        "output_model_repo": "owner/out",
        "adapters": [
            {"adapter_repo": "owner/a", "weight": 2},
            {"adapter_repo": "owner/b", "weight": 1},
        ],
    }

    normalized = module.normalize_profile(profile)

    assert normalized["adapters"][0]["weight"] == 2 / 3
    assert normalized["adapters"][1]["weight"] == 1 / 3


def test_build_packet_writes_merge_script_and_packet(tmp_path: Path) -> None:
    module = _load_module()
    profile_path = tmp_path / "merge_profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_coding_model_merge_profile_v1",
                "merge_id": "merge",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "output_model_repo": "owner/out",
                "merge_mode": "weighted",
                "adapters": [
                    {"profile_id": "v2", "adapter_repo": "owner/a", "weight": 0.25},
                    {"profile_id": "v6", "adapter_repo": "owner/b", "weight": 0.75},
                ],
            }
        ),
        encoding="utf-8",
    )

    packet = module.build_packet(profile_path, tmp_path / "runs", flavor="t4-small", timeout="30m")

    assert packet["schema_version"] == "scbe_coding_model_merge_job_packet_v1"
    assert packet["merge_mode"] == "weighted"
    assert packet["execution"]["flavor"] == "t4-small"
    assert packet["execution"]["timeout"] == "30m"
    assert Path(packet["script_path"]).exists()
    assert (Path(packet["run_dir"]) / "merge_packet.json").exists()
    script = Path(packet["script_path"]).read_text(encoding="utf-8")
    assert "add_weighted_adapter" in script
    assert "owner/out" in script

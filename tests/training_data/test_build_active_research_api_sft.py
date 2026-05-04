from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_active_research_api_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_active_research_api_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assistant_payload(row: dict) -> dict:
    content = row["messages"][-1]["content"]
    parsed = json.loads(content)
    assert isinstance(parsed, dict)
    return parsed


def test_build_records_are_json_handoffs_with_receipts_and_safety() -> None:
    module = _load_module()

    rows = module.build_records()

    assert len(rows) >= 8
    for row in rows:
        payload = _assistant_payload(row)
        assert payload["decision"]
        assert payload["primary_inlet"]
        assert payload["receipt_fields"]
        assert payload["safety_checks"]
        assert "api_keys" in payload["compact_handoff"]["exclude"]
        assert row["metadata"]["track"] == "active_research_api_usage_v1"


def test_training_lane_blocks_paid_model_api_collection() -> None:
    module = _load_module()

    rows = module.build_records()
    joined = "\n".join(json.dumps(row, sort_keys=True) for row in rows)

    assert "kimi_code_cli" not in joined
    assert "moonshot_openai_compatible" not in joined
    assert "no_paid_model_api" in joined
    assert "ALLOW_OPEN_KEYS_ONLY" in joined


def test_known_public_connectors_are_verified_from_registry() -> None:
    module = _load_module()

    rows = module.build_records()
    arxiv = next(row for row in rows if row["metadata"]["scenario"] == "arxiv_openalex_literature_scan")
    known = set(arxiv["metadata"]["known_connector_ids"])

    assert {"arxiv_api", "openalex_api", "crossref_rest"}.issubset(known)


def test_write_outputs_and_copy_kaggle(tmp_path: Path) -> None:
    module = _load_module()
    out_dir = tmp_path / "sft"
    kaggle_dir = tmp_path / "kaggle"

    result = module.write_outputs(out_dir, copy_kaggle=True, kaggle_dir=kaggle_dir)

    assert result["ok"] is True
    assert result["train_records"] > result["eval_records"] >= 1
    assert (out_dir / module.TRAIN_NAME).exists()
    assert (out_dir / module.EVAL_NAME).exists()
    assert (out_dir / module.MANIFEST_NAME).exists()
    assert (kaggle_dir / module.TRAIN_NAME).exists()
    assert (kaggle_dir / module.EVAL_NAME).exists()

    manifest = json.loads((out_dir / module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["gate"]["blocked"] == [
        "raw_api_keys",
        "unbounded_collection",
        "uncited_claims",
        "live_sensitive_targeting",
    ]

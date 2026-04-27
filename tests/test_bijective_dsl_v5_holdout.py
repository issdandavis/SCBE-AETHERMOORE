import json
from collections import Counter
from pathlib import Path

from scripts.dsl import build_v5_holdout


ROOT = Path(__file__).resolve().parents[1]
SFT = ROOT / "training-data" / "sft"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_v5_holdout_manifest_passes_after_build():
    assert build_v5_holdout.main() == 0

    manifest = json.loads((SFT / "bijective_dsl_v5_holdout_manifest.json").read_text(encoding="utf-8"))

    assert manifest["verdict"] == "PASS"
    assert manifest["boundary_check"]["repair_v3_train_overlap"] == 0
    assert manifest["translate_one_final"]["within_cap"] is True
    assert manifest["floor_check"]["violation_count"] == 0


def test_v5_holdout_category_floors_and_parametric_rows():
    rows = _load_jsonl(SFT / "bijective_dsl_v5_holdout.sft.jsonl")
    by_category = Counter(build_v5_holdout.category(row) for row in rows)

    for category in build_v5_holdout.FLOOR_BEARING:
        assert by_category[category] >= build_v5_holdout.WORKING_MIN

    parametric = [row for row in rows if row.get("meta", {}).get("provenance") == "parametric_generated_v5_holdout"]
    assert len(parametric) == 4
    assert {row["meta"]["task"] for row in parametric} == {"identify", "edit_slot_one"}

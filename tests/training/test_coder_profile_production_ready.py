import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "config" / "model_training" / "coder-qwen-code-primaries.json"


def test_coder_profile_excludes_eval_only_syntax_alignment_dataset():
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    dataset = profile["dataset"]
    all_files = dataset["train_files"] + dataset["eval_files"]
    assert "sacred_tongue_syntax_alignment_v1_train.sft.jsonl" not in all_files
    assert "sacred_tongue_syntax_alignment_v1_holdout.sft.jsonl" not in all_files


def test_coder_profile_keeps_production_coding_sources():
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    dataset = profile["dataset"]
    assert "bijective_codeflow_v1_train.sft.jsonl" in dataset["train_files"]
    assert "drill_langues_full_train.sft.jsonl" in dataset["train_files"]
    assert "bijective_codeflow_v1_holdout.sft.jsonl" in dataset["eval_files"]
    assert "drill_langues_full_holdout.sft.jsonl" in dataset["eval_files"]

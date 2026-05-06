import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "config" / "model_training" / "coding-approval-metrics-v3-hf.json"
MARKER_PROFILE_PATH = ROOT / "config" / "model_training" / "coding-approval-metrics-v3-marker-focus-hf.json"
SCAFFOLD_PROFILE_PATH = (
    ROOT / "config" / "model_training" / "coding-approval-metrics-v3-marker-focus-scaffold-hf.json"
)
DPO_PROFILE_PATH = ROOT / "config" / "model_training" / "coding-approval-metrics-v3-marker-dpo-hf.json"
CONTRACT_PATH = ROOT / "config" / "model_training" / "coding_approval_metrics_v3_eval_contract.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_forbidden_with_gate_boundaries(text: str, term: str) -> bool:
    body_lower = text.lower()
    needle = term.strip().lower()
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9_ -]+", needle):
        pattern_body = r"\s+".join(re.escape(part) for part in needle.split())
        pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
        return re.search(pattern, body_lower) is not None
    return needle in body_lower


def test_coding_approval_v3_hf_profile_has_real_files() -> None:
    profile = _load_json(PROFILE_PATH)
    dataset_root = ROOT / profile["dataset"]["root"]

    assert profile["profile_id"] == "coding-approval-metrics-v3-hf"
    assert profile["hub"]["push_adapter"] is True
    assert profile["execution"]["hf_flavor"] == "t4-small"
    assert profile["evaluation"]["contract_path"] == "config/model_training/coding_approval_metrics_v3_eval_contract.json"
    assert profile["evaluation"]["constrained_gate_scaffold"] is False
    assert profile["evaluation"]["constrained_prompt_prefix"] is True

    expected_eval = "functional_coding_benchmark_repairs_v1_eval.sft.jsonl"
    assert expected_eval in profile["dataset"]["eval_files"]

    for filename in profile["dataset"]["train_files"] + profile["dataset"]["eval_files"]:
        file_path = dataset_root / filename
        assert file_path.exists(), f"missing training file: {file_path}"
        assert file_path.stat().st_size > 0, f"empty training file: {file_path}"


def test_coding_approval_v3_contract_is_frozen_and_nonempty() -> None:
    contract = _load_json(CONTRACT_PATH)

    assert contract["contract_id"] == "coding_approval_metrics_v3_eval_contract"
    assert contract["thresholds"]["minimum_pass_rate"] == 0.8
    assert len(contract["prompts"]) >= 5
    assert set(contract["thresholds"]["must_pass"]).issubset({prompt["id"] for prompt in contract["prompts"]})

    for prompt in contract["prompts"]:
        assert prompt["required"], prompt["id"]
        assert prompt["forbidden"], prompt["id"]


def test_coding_approval_v3_contract_avoids_literal_token_collisions() -> None:
    contract = _load_json(CONTRACT_PATH)

    for prompt in contract["prompts"]:
        required = {token.casefold() for token in prompt["required"]}
        forbidden = {token.casefold() for token in prompt["forbidden"]}
        assert required.isdisjoint(forbidden), prompt["id"]

        prompt_text = prompt["prompt"].casefold()
        literal_forbidden = [token for token in forbidden if token in prompt_text]
        assert not literal_forbidden, f"{prompt['id']} prompt leaks forbidden tokens: {literal_forbidden}"


def test_coding_approval_v3_required_marker_prefix_does_not_trigger_forbidden_boundary_gate() -> None:
    contract = _load_json(CONTRACT_PATH)

    for prompt in contract["prompts"]:
        prefix = "REQUIRED_MARKERS=" + " | ".join(prompt["required"])
        forbidden_hits = [
            token for token in prompt["forbidden"] if _contains_forbidden_with_gate_boundaries(prefix, token)
        ]
        assert not forbidden_hits, f"{prompt['id']} required prefix triggers forbidden tokens: {forbidden_hits}"


def test_coding_approval_v3_contract_covers_verdict_vocabulary() -> None:
    contract = _load_json(CONTRACT_PATH)
    required_text = "\n".join("\n".join(prompt["required"]) for prompt in contract["prompts"])

    for verdict in ["PROMOTE", "HOLD", "INCUBATE", "TRANSFORM", "DENY"]:
        assert verdict in required_text


def test_coding_approval_v3_marker_focus_profile_is_exact_copy_repair_lane() -> None:
    profile = _load_json(MARKER_PROFILE_PATH)
    dataset_root = ROOT / profile["dataset"]["root"]

    assert profile["profile_id"] == "coding-approval-metrics-v3-marker-focus-hf"
    assert profile["hub"]["adapter_repo"].endswith("marker-focus-hf")
    assert profile["evaluation"]["contract_path"] == "config/model_training/coding_approval_metrics_v3_eval_contract.json"
    assert profile["evaluation"]["constrained_gate_scaffold"] is False
    assert profile["evaluation"]["constrained_prompt_prefix"] is True
    assert profile["training"]["max_steps"] >= 320
    assert profile["training"]["learning_rate"] <= 0.00004
    assert profile["dataset"]["train_files"] == ["coding_approval_metrics_v3_marker_train.sft.jsonl"]
    assert "coding_approval_metrics_v3_marker_eval.sft.jsonl" in profile["dataset"]["eval_files"]

    for filename in profile["dataset"]["train_files"] + profile["dataset"]["eval_files"]:
        file_path = dataset_root / filename
        assert file_path.exists(), f"missing marker-focus training file: {file_path}"
        assert file_path.stat().st_size > 0, f"empty marker-focus training file: {file_path}"


def test_coding_approval_v3_scaffold_profile_keeps_raw_diagnostic_but_uses_receipt_gate() -> None:
    profile = _load_json(SCAFFOLD_PROFILE_PATH)

    assert profile["profile_id"] == "coding-approval-metrics-v3-marker-focus-scaffold-hf"
    assert profile["hub"]["adapter_repo"].endswith("marker-focus-scaffold-hf")
    assert profile["dataset"]["train_files"] == ["coding_approval_metrics_v3_marker_train.sft.jsonl"]
    assert profile["evaluation"]["contract_path"] == "config/model_training/coding_approval_metrics_v3_eval_contract.json"
    assert profile["evaluation"]["constrained_gate_scaffold"] is True
    assert profile["evaluation"]["constrained_prompt_prefix"] is True
    assert any("raw_ok" in note or "Raw model responses" in note for note in profile["notes"])


def test_coding_approval_v3_marker_dpo_profile_uses_preference_repair() -> None:
    profile = _load_json(DPO_PROFILE_PATH)
    dataset_root = ROOT / profile["dataset"]["root"]

    assert profile["profile_id"] == "coding-approval-metrics-v3-marker-dpo-hf"
    assert profile["backend"] == "hf-jobs-peft-dpo"
    assert profile["training"]["base_adapter_repo"].endswith("marker-focus-scaffold-hf")
    assert profile["evaluation"]["contract_path"] == "config/model_training/coding_approval_metrics_v3_eval_contract.json"
    assert profile["evaluation"]["constrained_gate_scaffold"] is False
    assert profile["evaluation"]["constrained_prompt_prefix"] is True
    assert profile["training"]["learning_rate"] <= 0.00002
    assert profile["training"]["max_steps"] <= 120
    assert profile["dataset"]["train_files"] == ["coding_approval_marker_dpo_v1_train.jsonl"]

    for filename in profile["dataset"]["train_files"]:
        file_path = dataset_root / filename
        assert file_path.exists(), f"missing DPO training file: {file_path}"
        assert file_path.stat().st_size > 0, f"empty DPO training file: {file_path}"

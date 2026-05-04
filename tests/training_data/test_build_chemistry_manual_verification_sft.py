import json

from scripts.training_data import build_chemistry_manual_verification_sft as builder


def test_build_outputs_train_eval_and_manifest(tmp_path, monkeypatch):
    train_out = tmp_path / "train.sft.jsonl"
    eval_out = tmp_path / "eval.sft.jsonl"
    manifest_out = tmp_path / "manifest.json"
    monkeypatch.setattr(builder, "TRAIN_OUT", train_out)
    monkeypatch.setattr(builder, "EVAL_OUT", eval_out)
    monkeypatch.setattr(builder, "MANIFEST_OUT", manifest_out)

    manifest = builder.build(copy_kaggle=False)

    assert manifest["row_counts"]["source"] == 20
    assert manifest["row_counts"]["train"] > manifest["row_counts"]["eval"] >= 2
    assert train_out.exists()
    assert eval_out.exists()
    assert manifest_out.exists()


def test_records_have_openai_chat_shape_and_manual_path(tmp_path, monkeypatch):
    train_out = tmp_path / "train.sft.jsonl"
    eval_out = tmp_path / "eval.sft.jsonl"
    manifest_out = tmp_path / "manifest.json"
    monkeypatch.setattr(builder, "TRAIN_OUT", train_out)
    monkeypatch.setattr(builder, "EVAL_OUT", eval_out)
    monkeypatch.setattr(builder, "MANIFEST_OUT", manifest_out)

    builder.build(copy_kaggle=False)
    first = json.loads(train_out.read_text(encoding="utf-8").splitlines()[0])
    payload = json.loads(first["messages"][2]["content"])

    assert [msg["role"] for msg in first["messages"]] == ["system", "user", "assistant"]
    assert payload["schema_version"] == "scbe_chemistry_manual_verification_answer_v1"
    assert set(payload["manual_path"]) == {"valence", "electronegativity", "functional_group", "bond_analysis"}
    assert "expected_governance" in payload["verdict"]


def test_eval_keeps_invalid_boundary_case(tmp_path, monkeypatch):
    train_out = tmp_path / "train.sft.jsonl"
    eval_out = tmp_path / "eval.sft.jsonl"
    manifest_out = tmp_path / "manifest.json"
    monkeypatch.setattr(builder, "TRAIN_OUT", train_out)
    monkeypatch.setattr(builder, "EVAL_OUT", eval_out)
    monkeypatch.setattr(builder, "MANIFEST_OUT", manifest_out)

    builder.build(copy_kaggle=False)
    eval_rows = [json.loads(line) for line in eval_out.read_text(encoding="utf-8").splitlines()]

    assert any(row["metadata"]["expected_governance"] == "DENY" for row in eval_rows)
    assert any("pentavalent_carbon" in row["id"] for row in eval_rows)


def test_deterministic_output(tmp_path, monkeypatch):
    train_out = tmp_path / "train.sft.jsonl"
    eval_out = tmp_path / "eval.sft.jsonl"
    manifest_out = tmp_path / "manifest.json"
    monkeypatch.setattr(builder, "TRAIN_OUT", train_out)
    monkeypatch.setattr(builder, "EVAL_OUT", eval_out)
    monkeypatch.setattr(builder, "MANIFEST_OUT", manifest_out)

    first = builder.build(copy_kaggle=False)
    train_text = train_out.read_text(encoding="utf-8")
    eval_text = eval_out.read_text(encoding="utf-8")
    second = builder.build(copy_kaggle=False)

    assert train_out.read_text(encoding="utf-8") == train_text
    assert eval_out.read_text(encoding="utf-8") == eval_text
    assert first["hashes"]["train_sha256"] == second["hashes"]["train_sha256"]

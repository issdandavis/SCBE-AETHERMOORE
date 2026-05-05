from __future__ import annotations

import json
from pathlib import Path

from scripts.training_data.build_kinematic_mesh_filter_repair_sft import build_rows, write_outputs


def _write_residues(path: Path) -> None:
    rows = [
        {
            "schema_version": "scbe_agentic_training_residue_v1",
            "run_id": "unit-run",
            "contract_id": "chemistry_verification_unseen_eval_v1",
            "prompt_id": "chem_eval_pentavalent_carbon_reject",
            "kind": "boundary_residue",
            "ok": False,
            "missing_required": [],
            "triggered_forbidden": ["PASS", "promote"],
            "raw_missing_required": ["C(C)(C)(C)(C)C", "pentavalent"],
            "raw_triggered_forbidden": ["PASS"],
        },
        {
            "schema_version": "scbe_agentic_training_residue_v1",
            "run_id": "unit-run",
            "contract_id": "chemistry_verification_unseen_eval_v1",
            "prompt_id": "chem_eval_nacl_boundary",
            "kind": "repair_residue",
            "ok": False,
            "missing_required": ["sodium", "chloride"],
            "triggered_forbidden": [],
        },
        {
            "schema_version": "scbe_agentic_training_residue_v1",
            "run_id": "unit-run",
            "contract_id": "chemistry_verification_unseen_eval_v1",
            "prompt_id": "chem_eval_ethanol_route",
            "kind": "positive_residue",
            "ok": True,
            "token_chain": ["CCO", "carbon", "oxygen", "PASS"],
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_contract(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": "chem_eval_pentavalent_carbon_reject",
                        "prompt": "Reject the pentavalent carbon case.",
                        "required": ["C(C)(C)(C)(C)C", "carbon", "valence", "pentavalent", "invalid", "RDKit", "DENY"],
                        "forbidden": ["PASS", "promote", "drug-like"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_build_rows_uses_failed_residues_as_sacrificial_layer(tmp_path: Path) -> None:
    residue_path = tmp_path / "training_residues.jsonl"
    contract_path = tmp_path / "contract.json"
    _write_residues(residue_path)
    _write_contract(contract_path)

    train, eval_rows = build_rows(residue_path, contract_path=contract_path)

    assert len(train) == 12
    assert len(eval_rows) == 2
    assistant = train[0]["messages"][2]["content"]
    assert "REQUIRED_MARKERS=C(C)(C)(C)(C)C | carbon | valence | pentavalent | invalid | RDKit | DENY" in assistant
    assert "BOUNDARY_GUARD=PASS | promote | drug-like" in assistant
    assert "KINEMATIC_MESH_MODE=boundary_residue" in assistant
    assert "Governance verdict: DENY" in assistant
    assert train[0]["metadata"]["sacrificial_layer"] == "training_residue"
    assert train[0]["metadata"]["mesh_role"] == "reusable_gate_harness"
    assert "positive_residue" not in {row["metadata"]["source_kind"] for row in train + eval_rows}
    assert train[0]["metadata"]["repeat_index"] == 0
    assert train[0]["metadata"]["contract_augmented"] is True


def test_write_outputs_creates_manifest_and_jsonl(tmp_path: Path) -> None:
    residue_path = tmp_path / "training_residues.jsonl"
    contract_path = tmp_path / "contract.json"
    out_dir = tmp_path / "sft"
    _write_residues(residue_path)
    _write_contract(contract_path)

    result = write_outputs(residue_path, out_dir, include_positive=True, contract_path=contract_path)

    assert result["ok"] is True
    assert result["train_records"] == 17
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["pattern"]["reusable_mesh"] == "stable gate/harness"
    assert manifest["pattern"]["scab_ejection"].startswith("compact failed residues")
    assert manifest["repeats"] == 7
    assert manifest["source_contract"].endswith("contract.json")
    rows = [json.loads(line) for line in Path(result["train_path"]).read_text(encoding="utf-8").splitlines()]
    assert rows[0]["messages"][0]["content"].startswith("You are an SCBE-AETHERMOORE training repair agent")

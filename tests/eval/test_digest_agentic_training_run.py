from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.digest_agentic_training_run import (
    _extract_gate_report_from_log,
    _extract_losses_from_log,
    build_digest,
    write_outputs,
)


def _report(pass_rate: float = 1.0) -> dict:
    ok = pass_rate == 1.0
    return {
        "contract_id": "stage5_command_harmony_eval_v1",
        "n_total": 2,
        "n_pass": 2 if ok else 1,
        "pass_rate": pass_rate,
        "overall_pass": ok,
        "must_pass_all_ok": ok,
        "results": [
            {
                "id": "stage5_current_harness_terminal_command",
                "ok": True,
                "missing_required": [],
                "triggered_forbidden": [],
                "response": (
                    "required-tokens: `python -m src.geoseal_cli` | "
                    "harness-terminal | --models | ollama: | deepseek: | "
                    "--no-health | --json ::\nCommand follows."
                ),
            },
            {
                "id": "stage5_provider_lane_signal",
                "ok": ok,
                "missing_required": [] if ok else ["provider-pair:ollama->deepseek:benchmark"],
                "triggered_forbidden": [],
                "response": (
                    (
                        "required-tokens: provider-pair:ollama->deepseek:benchmark | "
                        "signal | blocked | lane | cost ::\nSignal follows."
                    )
                    if ok
                    else "Signal omitted."
                ),
            },
        ],
    }


def test_build_digest_extracts_positive_residue_chains() -> None:
    digest = build_digest(_report(), losses=[4.2, 0.25], run_id="unit-run")

    assert digest["next_phase"] == "promotion_packaging"
    assert digest["lane_allocation"] == {"explore": 10, "exploit": 90}
    assert digest["residue_count"] == 2
    assert digest["residues"][0]["kind"] == "positive_residue"
    assert "python -m src.geoseal_cli" in digest["residues"][0]["token_chain"]
    assert digest["loss"]["latest"] == 0.25


def test_build_digest_expands_state_space_on_low_loss_gate_failure() -> None:
    digest = build_digest(_report(pass_rate=0.25), losses=[4.2, 0.2], run_id="unit-run")

    assert digest["next_phase"] == "quadratic_expand_state_space"
    assert digest["lane_allocation"] == {"explore": 75, "exploit": 25}
    repair = [row for row in digest["residues"] if row["kind"] == "repair_residue"]
    assert repair
    assert repair[0]["token_chain"] == ["provider-pair:ollama->deepseek:benchmark"]


def test_extract_gate_report_and_losses_from_hf_log(tmp_path: Path) -> None:
    wrapped = {"event": "gate_report", "report": _report()}
    log = tmp_path / "hf.log"
    log.write_text(
        "{'loss': '4.215', 'epoch': '2'}\n" "{'loss': '0.2556', 'epoch': '24'}\n" + json.dumps(wrapped) + "\n",
        encoding="utf-8",
    )

    report = _extract_gate_report_from_log(log)
    losses = _extract_losses_from_log(log)

    assert report["contract_id"] == "stage5_command_harmony_eval_v1"
    assert losses == [4.215, 0.2556]


def test_write_outputs_creates_digest_and_residue_jsonl(tmp_path: Path) -> None:
    digest = build_digest(_report(), losses=[1.0], run_id="unit-run")
    paths = write_outputs(digest, tmp_path)

    digest_path = Path(paths["digest"])
    residue_path = Path(paths["residues"])
    assert digest_path.exists()
    assert residue_path.exists()
    assert json.loads(digest_path.read_text(encoding="utf-8"))["run_id"] == "unit-run"
    assert len(residue_path.read_text(encoding="utf-8").splitlines()) == 2

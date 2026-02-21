from __future__ import annotations

from pathlib import Path

from src.harmonic.sheaf_consensus_gate import run_jsonl, sheaf_gate, sheaf_stability


def test_sheaf_gate_allows_low_risk_inputs() -> None:
    res = sheaf_gate(
        fast_signal=0.05,
        memory_signal=0.10,
        governance_signal=0.08,
        pqc_valid=1.0,
        harm_score=0.95,
        drift_factor=0.92,
        spectral_score=0.90,
    )
    assert res.decision == "ALLOW"
    assert 0.70 <= res.omega <= 1.0


def test_sheaf_gate_denies_when_pqc_invalid() -> None:
    res = sheaf_gate(
        fast_signal=0.10,
        memory_signal=0.10,
        governance_signal=0.10,
        pqc_valid=0.0,
    )
    assert res.decision == "DENY"
    assert res.omega == 0.0


def test_sheaf_stability_reports_obstructions_for_conflict() -> None:
    stable, obs, assignment, projected = sheaf_stability(
        fast_signal=0.95,
        memory_signal=0.05,
        governance_signal=0.95,
    )
    assert obs >= 1
    assert 0.0 <= stable <= 1.0
    assert set(assignment.keys()) == {"Ti", "Tm", "Tg"}
    assert set(projected.keys()) == {"Ti", "Tm", "Tg"}


def test_run_jsonl_writes_gate_results(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    inp.write_text(
        "\n".join(
            [
                '{"fast_signal":0.1,"memory_signal":0.1,"governance_signal":0.1}',
                '{"fast_signal":0.9,"memory_signal":0.9,"governance_signal":0.9,"harm_score":0.2}',
            ]
        ),
        encoding="utf-8",
    )
    counts = run_jsonl(inp, out)
    assert out.exists()
    lines = [x for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 2
    assert sum(counts.values()) == 2


from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "eval" / "score_packet_trace_sft.py"
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "training" / "generate_packet_traces_sft.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("score_packet_trace_sft", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_packet_traces_sft", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_bytes(payload.encode("utf-8"))


def test_packet_trace_gate_passes_generated_corpus(tmp_path: Path) -> None:
    gate = _load_script()
    generator = _load_generator()
    corpus = tmp_path / "packet_traces.jsonl"
    rows = generator.generate_pairs()
    _write_rows(corpus, rows)

    report = gate.score_packet_trace_corpus(corpus)

    assert report["pass"] is True
    assert report["rows"] == 24
    assert report["trace_count"] == 6
    assert report["verdict_count"] == 18
    assert report["tongues"] == ["AV", "CA", "DR", "KO", "RU", "UM"]
    assert report["byte_deterministic"] is True


def test_packet_trace_gate_fails_on_fingerprint_tamper(tmp_path: Path) -> None:
    gate = _load_script()
    generator = _load_generator()
    corpus = tmp_path / "packet_traces.jsonl"
    rows = generator.generate_pairs()
    rows[0]["metadata"]["packet_fingerprint"] = "pkt:tampered"
    _write_rows(corpus, rows)

    report = gate.score_packet_trace_corpus(corpus)

    assert report["pass"] is False
    assert report["verdict_fingerprint_failures"] == 1


def test_packet_trace_gate_fails_on_forbidden_prose_token(tmp_path: Path) -> None:
    gate = _load_script()
    generator = _load_generator()
    corpus = tmp_path / "packet_traces.jsonl"
    rows = generator.generate_pairs()
    rows[0]["response"] += "<tool_call>"
    _write_rows(corpus, rows)

    report = gate.score_packet_trace_corpus(corpus)

    assert report["pass"] is False
    assert report["forbidden_token_failures"] == 1


def test_packet_trace_gate_cli(tmp_path: Path) -> None:
    generator = _load_generator()
    corpus = tmp_path / "packet_traces.jsonl"
    _write_rows(corpus, generator.generate_pairs())

    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--corpus", str(corpus), "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["pass"] is True
    assert report["gate"] == "packet_trace_sft_v1"

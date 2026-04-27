from __future__ import annotations

import json

from scripts.aetherpp_interpreter import AetherPPInterpreter, main
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER


PROGRAM = """
create spacaita system with 4 manifolds.
apply discrete fold 0.8 to manifold 0 with goal 0.95 in tongue KO.
cross propagate from manifold 0 to manifold 2.
encode "def add(a, b): return a + b" and seal with GeoSeal in tongue KO.
run route.
"""


def test_aetherpp_emits_route_payload_with_round_trip_tokens() -> None:
    payload = AetherPPInterpreter().interpret(PROGRAM)

    assert payload["schema_version"] == "aetherpp_route_payload_v1"
    assert payload["intent_gate"]["status"] == "metadata_only"
    assert payload["route_request"]["language"] == "python"
    assert payload["route_request"]["tongue"] == "KO"
    assert payload["manifolds"][0]["count"] == 4
    assert payload["manifolds"][1]["tier"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert payload["propagations"] == [{"event": "cross_propagate", "source": 0, "target": 2}]

    stream = payload["token_streams"][0]
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(stream["tongue"].lower(), stream["tokens"])
    assert decoded.decode("utf-8") == "def add(a, b): return a + b"
    assert stream["round_trip"] is True
    assert len(stream["seal"]) == 64


def test_aetherpp_cli_writes_execution_shell(tmp_path, monkeypatch) -> None:
    out = tmp_path / "execution_shell.json"
    monkeypatch.setattr("sys.argv", ["aetherpp", PROGRAM, "--out", str(out)])

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["route_request"]["source_name"] == "aetherpp://inline"
    assert payload["run_requested"] is True

from __future__ import annotations

import json

from src.geoseal_cli import main


def test_arc_tokenize_uses_real_faces_and_opcode_registry(capsys, tmp_path):
    package = tmp_path / "arc_prize_2026"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "generic.py").write_text(
        """
def synthesize_rules(task):
    def identity(grid):
        return tuple(tuple(value for value in row) for row in grid)
    return [("panels:horizontal:2:0:1:xor", 7, identity)]
""".lstrip(),
        encoding="utf-8",
    )
    challenges = tmp_path / "challenges.json"
    challenges.write_text(
        json.dumps(
            {
                "demo": {
                    "train": [{"input": [[0, 1], [1, 0]], "output": [[0, 1], [1, 0]]}],
                    "test": [{"input": [[1, 0], [0, 1]]}],
                }
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "arc-tokenize",
            "--task",
            "demo",
            "--arc-root",
            str(tmp_path),
            "--challenges",
            str(challenges),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["lane_order"] == ["OBS", "FEAT", "REL", "HYP", "ACT", "ASSERT", "MEM"]
    assert payload["face_order"] == ["KO", "AV", "RU", "CA", "UM", "DR", "ARC_ATOMIC"]
    assert payload["promotion"]["gate"] == "PASS"
    assert payload["reversible"] is True
    assert all(record["reversible"] for record in payload["records"])

    actions = [record for record in payload["records"] if record["lane"] == "ACT"]
    xor = next(record for record in actions if record["canonical_id"] == "ARC.ACT.OPCODE.XOR")
    panels = next(record for record in actions if record["canonical_id"] == "ARCX.ACT.PANELS")
    assert xor["execution"]["registry"] == "python.scbe.ca_opcode_table.OP_TABLE"
    assert xor["execution"]["op_id"] == 19
    assert xor["execution"]["executable"] is True
    assert panels["execution"]["op_id"] is None
    assert panels["execution"]["executable"] is False
    assert all("execution" not in record for record in payload["records"] if record["lane"] != "ACT")

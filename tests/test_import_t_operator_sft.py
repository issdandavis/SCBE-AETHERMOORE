import json

from scripts.import_t_operator_sft import import_dataset


def test_import_t_operator_sft_converts_kimi_rows_to_messages_format(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "out.sft.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text(
        json.dumps(
            {
                "instruction": "Construct Constant 1.",
                "input": "Target: Constant 1",
                "output": "SOLUTION: T(s,s,s) = 1",
                "system": "Compiler system.",
                "metadata": {
                    "function_key": "const_1",
                    "verified": True,
                    "rpn": "s s s T",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = import_dataset(source, output, manifest)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert payload["record_count"] == 1
    assert payload["verified_count"] == 1
    assert rows[0]["track"] == "t_operator_eml_symbolic_compiler"
    assert rows[0]["messages"][0]["role"] == "system"
    assert rows[0]["messages"][1]["role"] == "user"
    assert rows[0]["messages"][2]["content"] == "SOLUTION: T(s,s,s) = 1"
    assert rows[0]["metadata"]["operator_primitives"] == ["T(x,y,z)", "EML(x,y)"]
    assert json.loads(manifest.read_text(encoding="utf-8"))["record_count"] == 1

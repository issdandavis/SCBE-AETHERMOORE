import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def test_builder_emits_schema_valid_records(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    corpus_path = tmp_path / "sample_route_records.jsonl"
    records = [
        {
            "messages": [
                {"role": "system", "content": "Layer 3 operator"},
                {"role": "user", "content": "Implement a safe file parser in Python."},
                {"role": "assistant", "content": "Use pathlib, validate suffixes, and reject traversal."},
            ],
            "task_type": "l3",
        },
        {
            "instruction": "Implement a safe file parser in Python.",
            "response": "Use pathlib, validate suffixes, and reject traversal.",
            "metadata": {"source_file": "src/parser.py", "origin": "codebase_docs"},
        },
    ]
    corpus_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    output_path = tmp_path / "route_consistency_records.jsonl"
    manifest_path = tmp_path / "manifest.json"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "build_route_consistency_records.py"),
            "--input",
            str(corpus_path),
            "--output-jsonl",
            str(output_path),
            "--manifest-path",
            str(manifest_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout.strip())
    assert summary["record_count"] == 2

    schema = json.loads((repo_root / "schemas" / "route_consistency_record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    emitted = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(emitted) == 2
    for record in emitted:
        validator.validate(record)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["record_count"] == 2
    assert manifest["intent_count"] == 1

import json

from scripts.build_binary_pillars_sft import (
    build_records,
    byte_to_element_index,
    write_dataset,
)


def _assistant_payload(record):
    assistant = record["messages"][-1]["content"]
    return json.loads(assistant)


def test_byte_to_element_index_is_bounded() -> None:
    values = [byte_to_element_index(value) for value in range(256)]

    assert min(values) >= 1
    assert max(values) <= 118


def test_binary_pillar_records_preserve_round_trip_invariants() -> None:
    records = build_records()

    assert len(records) == 39
    for record in records:
        payload = _assistant_payload(record)
        binary = payload["binary_pillar"]["binary"]
        decimal = payload["binary_pillar"]["decimal"]
        assert int(binary, 2) == decimal
        assert payload["round_trip"]["binary_to_decimal"] == decimal
        assert payload["round_trip"]["decimal_to_binary"] == binary
        assert set(payload["code_pillar"]) == {"python", "typescript", "c", "rust"}
        assert payload["invariant"].startswith("All pillars describe the same substrate value")


def test_write_dataset_outputs_jsonl_and_manifest(tmp_path) -> None:
    output = tmp_path / "binary_pillars.sft.jsonl"
    manifest_path = tmp_path / "manifest.json"

    manifest = write_dataset(output, manifest_path)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert manifest["record_count"] == 39
    assert len(lines) == 39
    assert json.loads(lines[0])["track"] == "binary_music_atomic_code_pillars"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["record_count"] == 39

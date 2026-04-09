import json

import pytest

from scripts.build_route_consistency_records import build_records_from_paths


def test_builder_groups_related_routes_by_intent(tmp_path):
    corpus_path = tmp_path / "mixed.jsonl"
    rows = [
        {
            "messages": [
                {"role": "user", "content": "Review this function for SQL injection."},
                {"role": "assistant", "content": "Parameterize the query and reject string concatenation."},
            ],
            "task_type": "L5",
        },
        {
            "prompt": "Review this function for SQL injection.",
            "response": "Parameterize the query and reject string concatenation.",
            "source": "codeql_fix",
        },
    ]
    corpus_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    records = build_records_from_paths([corpus_path], tmp_path)
    assert len(records) == 2
    assert records[0]["intent_id"] == records[1]["intent_id"]
    assert records[0]["target_cluster"] == records[1]["target_cluster"]
    assert records[0]["triangulation_links"][0]["linked_record_ids"] == [records[1]["record_id"]]
    assert records[1]["triangulation_links"][0]["linked_record_ids"] == [records[0]["record_id"]]
    assert len(records[0]["atomic_features"]["tokens"]) == len(records[0]["atomic_features"]["elements"])
    assert len(records[0]["atomic_features"]["tokens"]) == len(records[0]["atomic_features"]["trits"])


def test_builder_fails_fast_on_unsupported_rows(tmp_path):
    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(json.dumps({"foo": "bar"}) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported row shape"):
        build_records_from_paths([bad_path], tmp_path)

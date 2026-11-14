from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from python.scbe.prime_token_independent_replay import (
    _rebuild_packet_free_authority,
)
from python.scbe.prime_token_packet_free_authority import (
    IDENTITY_TRANSFORM,
    LINE_STRIP_JOIN_TRANSFORM,
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    PACKET_FREE_FAMILY_PREFIX,
    packet_free_family_id,
    validate_packet_free_rows,
)


def _authority_fixture(tmp_path: Path, *, lane: str = "ordinary") -> tuple[Path, Path, list[dict]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    first = "  first exact packet-free prompt  "
    second = "second exact packet-free prompt"
    separator = "\n"
    source = tmp_path / f"{lane}-source.txt"
    source.write_text(first + separator + second, encoding="utf-8", newline="")
    first_bytes = first.encode("utf-8")
    second_start = len(first_bytes) + len(separator.encode("utf-8"))
    rows = [
        {
            "id": f"{lane}-1",
            "text": first,
            "source_locator": f"fixture://{lane}/1",
            "content_sha256": sha256(first_bytes).hexdigest(),
        },
        {
            "id": f"{lane}-2",
            "text": second,
            "source_locator": f"fixture://{lane}/2",
            "content_sha256": sha256(second.encode("utf-8")).hexdigest(),
        },
    ]
    authority = {
        "schema": PACKET_FREE_AUTHORITY_SCHEMA,
        "lane": lane,
        "review_status": "ADMITTED",
        "authority": {
            "training_intake": NO_AUTHORITY,
            "optimization": NO_AUTHORITY,
            "promotion": NO_AUTHORITY,
            "partial_unfreeze": NO_AUTHORITY,
            "tool_dispatch": NO_AUTHORITY,
        },
        "sources": [
            {
                "path": str(source.resolve()),
                "sha256": sha256(source.read_bytes()).hexdigest(),
                "bytes": source.stat().st_size,
                "records": [
                    {
                        "id": rows[0]["id"],
                        "source_locator": rows[0]["source_locator"],
                        "byte_start": 0,
                        "byte_end": len(first_bytes),
                        "excerpt_sha256": rows[0]["content_sha256"],
                        "text_transform": IDENTITY_TRANSFORM,
                        "content_sha256": rows[0]["content_sha256"],
                    },
                    {
                        "id": rows[1]["id"],
                        "source_locator": rows[1]["source_locator"],
                        "byte_start": second_start,
                        "byte_end": second_start + len(second.encode("utf-8")),
                        "excerpt_sha256": rows[1]["content_sha256"],
                        "text_transform": IDENTITY_TRANSFORM,
                        "content_sha256": rows[1]["content_sha256"],
                    },
                ],
            }
        ],
    }
    authority_path = tmp_path / f"{lane}-authority.json"
    authority_path.write_text(json.dumps(authority), encoding="utf-8")
    return source, authority_path, rows


def test_canonicalizes_rows_with_authority_derived_family_and_exact_spans(
    tmp_path: Path,
) -> None:
    source, authority, rows = _authority_fixture(tmp_path)

    canonical, receipt = validate_packet_free_rows(rows, authority_path=authority, lane="ordinary")

    family = packet_free_family_id(authority)
    assert family.startswith(PACKET_FREE_FAMILY_PREFIX)
    assert receipt["family_id"] == family
    assert receipt["record_count"] == 2
    assert receipt["source_sha256s"] == [sha256(source.read_bytes()).hexdigest()]
    assert {row["source_family"] for row in canonical} == {family}
    assert canonical[0]["source_byte_start"] == 0
    assert canonical[0]["source_byte_end"] == len(rows[0]["text"].encode("utf-8"))
    assert canonical[0]["source_excerpt_sha256"] == rows[0]["content_sha256"]
    assert canonical[0]["text_transform"] == IDENTITY_TRANSFORM
    assert canonical[0]["token_ids"] == list(rows[0]["text"].encode("utf-8"))


def test_applies_named_line_strip_join_transform_with_raw_excerpt_receipt(
    tmp_path: Path,
) -> None:
    excerpt = "  if ready:\n      do_it()\n\n  return done\n"
    expected = "if ready: do_it() return done"
    source = tmp_path / "transformed-source.txt"
    source.write_text(excerpt, encoding="utf-8", newline="")
    source_bytes = source.read_bytes()
    row = {
        "id": "ordinary-transformed",
        "text": expected,
        "source_locator": "fixture://ordinary/transformed",
        "content_sha256": sha256(expected.encode("utf-8")).hexdigest(),
    }
    authority = {
        "schema": PACKET_FREE_AUTHORITY_SCHEMA,
        "lane": "ordinary",
        "review_status": "ADMITTED",
        "authority": {
            "training_intake": NO_AUTHORITY,
            "optimization": NO_AUTHORITY,
            "promotion": NO_AUTHORITY,
            "partial_unfreeze": NO_AUTHORITY,
            "tool_dispatch": NO_AUTHORITY,
        },
        "sources": [
            {
                "path": str(source.resolve()),
                "sha256": sha256(source_bytes).hexdigest(),
                "bytes": len(source_bytes),
                "records": [
                    {
                        "id": row["id"],
                        "source_locator": row["source_locator"],
                        "byte_start": 0,
                        "byte_end": len(source_bytes),
                        "excerpt_sha256": sha256(source_bytes).hexdigest(),
                        "text_transform": LINE_STRIP_JOIN_TRANSFORM,
                        "content_sha256": row["content_sha256"],
                    }
                ],
            }
        ],
    }
    authority_path = tmp_path / "transformed-authority.json"
    authority_path.write_text(json.dumps(authority), encoding="utf-8")

    canonical, receipt = validate_packet_free_rows([row], authority_path=authority_path, lane="ordinary")
    replay_receipt = _rebuild_packet_free_authority(authority_path, canonical, lane="ordinary")

    assert canonical[0]["text"] == expected
    assert canonical[0]["source_excerpt_sha256"] == sha256(source_bytes).hexdigest()
    assert canonical[0]["text_transform"] == LINE_STRIP_JOIN_TRANSFORM
    assert canonical[0]["token_ids"] == list(expected.encode("utf-8"))
    assert replay_receipt == receipt


def test_rejects_human_label_even_when_it_looks_disjoint(tmp_path: Path) -> None:
    _source, authority, rows = _authority_fixture(tmp_path)
    rows[0]["source_family"] = "python-cpython-documentation"

    with pytest.raises(ValueError, match="not authority-derived"):
        validate_packet_free_rows(rows, authority_path=authority, lane="ordinary")


def test_rejects_row_text_or_digest_not_equal_to_authorized_transform(
    tmp_path: Path,
) -> None:
    _source, authority, rows = _authority_fixture(tmp_path)
    changed = deepcopy(rows)
    changed[0]["text"] = "rewritten prompt"
    changed[0]["content_sha256"] = sha256(changed[0]["text"].encode("utf-8")).hexdigest()

    with pytest.raises(ValueError, match="authorized source transform"):
        validate_packet_free_rows(changed, authority_path=authority, lane="ordinary")

    changed = deepcopy(rows)
    changed[0]["content_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs from its text or source transform"):
        validate_packet_free_rows(changed, authority_path=authority, lane="ordinary")


def test_rejects_source_artifact_drift_after_authority_is_written(
    tmp_path: Path,
) -> None:
    source, authority, rows = _authority_fixture(tmp_path)
    source.write_text("changed after admission", encoding="utf-8")

    with pytest.raises(RuntimeError, match="artifact hash differs"):
        validate_packet_free_rows(rows, authority_path=authority, lane="ordinary")


def test_rejects_authority_escalation_and_unconsumed_records(tmp_path: Path) -> None:
    _source, authority, rows = _authority_fixture(tmp_path)
    value = json.loads(authority.read_text(encoding="utf-8"))
    value["authority"]["training_intake"] = "AUTHORIZED"
    authority.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpectedly authorizes training_intake"):
        validate_packet_free_rows(rows, authority_path=authority, lane="ordinary")

    _source, authority, rows = _authority_fixture(tmp_path / "fresh")
    with pytest.raises(ValueError, match="unconsumed records"):
        validate_packet_free_rows(rows[:1], authority_path=authority, lane="ordinary")

"""Tests for the non-launchable frozen-action candidate bundle."""

from __future__ import annotations

from scripts.research.build_frozen_action_candidate_bundle import (
    ACCEPTED_CAMPAIGN_SCHEMA,
    CANDIDATE_MANIFEST_SCHEMA,
    _authority,
    _sha256_json,
    _validate_bundle,
)


def _record(record_id: str, source_id: str, lane: str, prompt: str, digest: str) -> dict:
    return {
        "id": record_id,
        "input": prompt,
        "review_status": "NOT_REVIEWED",
        "source_id": source_id,
        "source_kind": "published_source",
        "source_sha256": digest,
        "split": lane,
        "training_eligible": False,
    }


def test_candidate_schema_cannot_be_mistaken_for_campaign_schema() -> None:
    assert CANDIDATE_MANIFEST_SCHEMA != ACCEPTED_CAMPAIGN_SCHEMA


def test_authority_receipt_replays() -> None:
    row = _authority(
        source_id="source-1",
        source_family="family-1",
        lane="ordinary",
        locator="https://example.invalid/repo@commit:path#lines=0:1",
        artifact_sha256="a" * 64,
        artifact_bytes=100,
        span={"end": 1, "start": 0, "unit": "line"},
        excerpt_sha256="b" * 64,
    )
    unsigned = dict(row)
    receipt = unsigned.pop("receipt_sha256")
    assert receipt == _sha256_json(unsigned)


def test_validation_requires_disjoint_four_lane_coverage() -> None:
    records: dict[str, list[dict]] = {}
    authorities: list[dict] = []
    for index, lane in enumerate(("train", "holdout", "ordinary", "retention")):
        source_id = f"source-{lane}"
        digest = f"{index + 1:x}" * 64
        records[lane] = [_record(f"record-{lane}", source_id, lane, f"prompt {lane}", digest)]
        authorities.append(
            _authority(
                source_id=source_id,
                source_family=f"family-{lane}",
                lane=lane,
                locator=f"https://example.invalid/{lane}",
                artifact_sha256="a" * 64,
                artifact_bytes=100,
                span={"end": 1, "start": 0, "unit": "record"},
                excerpt_sha256=digest,
            )
        )

    result = _validate_bundle(records, authorities)
    assert result["record_count"] == 4
    assert result["source_family_disjoint"] is True
    assert result["exact_prompt_disjoint"] is True

    authorities[-1]["source_family"] = authorities[0]["source_family"]
    unsigned = dict(authorities[-1])
    unsigned.pop("receipt_sha256")
    authorities[-1]["receipt_sha256"] = _sha256_json(unsigned)
    try:
        _validate_bundle(records, authorities)
    except ValueError as error:
        assert "source families overlap" in str(error)
    else:
        raise AssertionError("cross-lane source-family reuse was not rejected")

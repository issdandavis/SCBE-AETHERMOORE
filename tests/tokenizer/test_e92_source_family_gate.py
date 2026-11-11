from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.tokenizer.audit_e92_source_family_gate import audit_family_gate


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _fixture(tmp_path: Path, *, collapsed: bool = False) -> dict[str, Path]:
    database_hash = "d" * 64
    canonical_sources = []
    inventory_sources = []
    source_count = 1 if collapsed else 6
    for index in range(source_count):
        source = tmp_path / f"source-{index}.md"
        source.write_text(f"source {index}", encoding="utf-8")
        canonical_sources.append(
            {
                "path": str(source),
                "family_id": f"family-{index // 3}",
                "source_kind": "documentation",
                "license_name": "owner",
                "content_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "catalog_source_rows": 6 if collapsed else 1,
            }
        )
    for index in range(6):
        canonical = canonical_sources[0 if collapsed else index]
        uri = canonical["path"] + (f"#L{index + 1}" if collapsed else "")
        inventory_sources.append({"source_uri": uri, "unique_suffix": f"source-{index}"})
    audit = _write(
        tmp_path / "audit.json",
        {
            "schema": "scbe.prime-token-source-family-audit.v1",
            "error_count": 0,
            "catalog": {"database_sha256": database_hash},
            "canonical_sources": canonical_sources,
        },
    )
    inventory = _write(
        tmp_path / "inventory.json",
        {
            "schema": "clay.prime-token-catalog-source-suffixes.v1",
            "catalog_sha256": database_hash,
            "source_count": 6,
            "sources": inventory_sources,
        },
    )
    labels = []
    for index in range(30):
        labels.append(
            {
                "query_sha256": f"{index:064x}",
                "decision": "accept",
                "relevant_source_suffix": f"source-{index % 6}",
            }
        )
    label_path = _write(
        tmp_path / "labels.json",
        {
            "schema": "scbe.prime-token-independent-review-labels.v1",
            "labels": labels,
        },
    )
    return {"audit": audit, "inventory": inventory, "labels": label_path}


def _audit(paths: dict[str, Path]) -> dict:
    return audit_family_gate(
        source_family_audit=paths["audit"],
        source_inventory=paths["inventory"],
        labels=paths["labels"],
    )


def test_accepts_six_canonical_sources_across_two_families(tmp_path: Path) -> None:
    report = _audit(_fixture(tmp_path))

    assert report["status"] == "VERIFIED_SOURCE_FAMILY_DIVERSITY"
    assert report["error_count"] == 0
    assert report["observed"]["canonical_source_count"] == 6
    assert report["observed"]["manifest_bound_family_count"] == 2
    assert all(report["gates"].values())
    assert report["authority"]["scoring"] == "NOT_AUTHORIZED"


def test_six_line_suffixes_collapse_to_one_source_and_family(tmp_path: Path) -> None:
    report = _audit(_fixture(tmp_path, collapsed=True))

    assert report["status"] == "SOURCE_FAMILY_DIVERSITY_UNDERPOWERED"
    assert report["error_count"] == 0
    assert report["observed"]["catalog_row_source_count"] == 6
    assert report["observed"]["canonical_source_count"] == 1
    assert report["observed"]["manifest_bound_family_count"] == 1
    assert report["gates"]["minimum_canonical_sources"] is False
    assert report["gates"]["minimum_manifest_bound_families"] is False


def test_rejects_inventory_from_another_catalog(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    inventory = json.loads(paths["inventory"].read_text(encoding="utf-8"))
    inventory["catalog_sha256"] = "0" * 64
    _write(paths["inventory"], inventory)

    report = _audit(paths)

    assert report["status"] == "INVALID_SOURCE_FAMILY_GATE"
    assert "source inventory targets a different catalog" in report["errors"]


def test_rejects_inventory_row_without_canonical_binding(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    inventory = json.loads(paths["inventory"].read_text(encoding="utf-8"))
    inventory["sources"][0]["source_uri"] = str(tmp_path / "not-declared.md")
    _write(paths["inventory"], inventory)

    report = _audit(paths)

    assert report["status"] == "INVALID_SOURCE_FAMILY_GATE"
    assert any("not bound to a canonical source" in error for error in report["errors"])

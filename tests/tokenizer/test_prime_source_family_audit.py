from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from scripts.tokenizer.audit_prime_source_families import audit_source_families, sha256_file


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_id(uri: str, content_sha256: str) -> str:
    payload = "\x1f".join(("source", uri, content_sha256))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    conversation = tmp_path / "conversation.jsonl"
    conversation_rows = [
        {"source_session": "session-frozen", "text": "alpha"},
        {"source_session": "session-frozen", "text": "beta"},
    ]
    conversation.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in conversation_rows),
        encoding="utf-8",
    )
    code = tmp_path / "code.py"
    code.write_bytes(b"print('ok')\n")
    conversation_manifest = _write_json(
        tmp_path / "conversation-manifest.json",
        {
            "schema": "scbe.prime-token-source-manifest.v1",
            "sources": [
                {
                    "path": str(conversation),
                    "sha256": sha256_file(conversation),
                    "source_kind": "conversation",
                    "license": "owner",
                }
            ],
        },
    )
    code_manifest = _write_json(
        tmp_path / "code-manifest.json",
        {
            "schema": "scbe.prime-token-source-manifest.v1",
            "sources": [
                {
                    "path": str(code),
                    "sha256": sha256_file(code),
                    "source_kind": "code",
                    "license": "MIT",
                }
            ],
        },
    )
    database = tmp_path / "catalog.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE sources (source_id TEXT PRIMARY KEY, source_uri TEXT NOT NULL, "
        "source_kind TEXT NOT NULL, license_name TEXT NOT NULL, content_sha256 TEXT NOT NULL, "
        "byte_count INTEGER NOT NULL)"
    )
    for line_number, row in enumerate(conversation_rows, 1):
        uri = f"{conversation}#L{line_number}"
        content_sha256 = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        connection.execute(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
            (_source_id(uri, content_sha256), uri, "conversation", "owner", content_sha256, len(row["text"])),
        )
    code_sha256 = sha256_file(code)
    connection.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
        (_source_id(str(code), code_sha256), str(code), "code", "MIT", code_sha256, code.stat().st_size),
    )
    connection.commit()
    connection.close()
    manifest = _write_json(
        tmp_path / "MANIFEST.json",
        {
            "schema": "scbe.prime-token-catalog.v1",
            "source_count": 3,
            "outputs": [{"path": str(database), "sha256": sha256_file(database)}],
            "source_manifests": [
                {
                    "path": str(conversation_manifest),
                    "sha256": sha256_file(conversation_manifest),
                    "declared_sources": 1,
                },
                {
                    "path": str(code_manifest),
                    "sha256": sha256_file(code_manifest),
                    "declared_sources": 1,
                },
            ],
        },
    )
    watcher = _write_json(
        tmp_path / "WATCHER_STATUS.json",
        {
            "schema": "clay.codex-prospective-watcher.v1",
            "status": "WAITING_FOR_SESSION_CLOSE",
            "catalog_boundary": {
                "catalog_sha256": sha256_file(database),
                "manifest_sha256": sha256_file(manifest),
            },
            "catalog_conversation_boundary": {
                "conversation_rows": 2,
                "conversation_sources": 1,
                "conversation_sessions": 1,
                "source_manifests": 2,
            },
            "closed_post_freeze_source_count": 0,
            "open_post_freeze_source_count": 1,
            "source_session_disjoint": True,
            "deferred_open_source_session_disjoint": True,
            "scoring": "NOT_AUTHORIZED",
            "training_intake": "NOT_AUTHORIZED",
            "promotion": "NOT_AUTHORIZED",
        },
    )
    return {"manifest": manifest, "database": database, "watcher": watcher, "conversation": conversation}


def _audit(paths: dict[str, Path]) -> dict:
    return audit_source_families(
        catalog_manifest=paths["manifest"],
        catalog_database=paths["database"],
        watcher_status=paths["watcher"],
    )


def test_collapses_fragments_into_canonical_sources_and_families(tmp_path: Path) -> None:
    result = _audit(_fixture(tmp_path))

    assert result["status"] == "VERIFIED_SOURCE_FAMILY_BOUNDARY_WAITING"
    assert result["error_count"] == 0
    assert result["counts"]["catalog_source_rows"] == 3
    assert result["counts"]["canonical_sources"] == 2
    assert result["counts"]["manifest_bound_source_families"] == 2
    assert result["counts"]["conversation_source_rows"] == 2
    assert result["counts"]["conversation_source_sessions"] == 1
    assert result["prospective"]["evaluation_ready"] is False
    assert result["authority"]["promotion"] == "NOT_AUTHORIZED"


def test_rejects_undeclared_catalog_source(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    undeclared = tmp_path / "undeclared.txt"
    undeclared.write_bytes(b"hidden")
    digest = sha256_file(undeclared)
    connection = sqlite3.connect(paths["database"])
    connection.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
        (_source_id(str(undeclared), digest), str(undeclared), "code", "MIT", digest, undeclared.stat().st_size),
    )
    connection.commit()
    connection.close()
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    manifest["source_count"] = 4
    manifest["outputs"][0]["sha256"] = sha256_file(paths["database"])
    _write_json(paths["manifest"], manifest)
    watcher = json.loads(paths["watcher"].read_text(encoding="utf-8"))
    watcher["catalog_boundary"]["catalog_sha256"] = sha256_file(paths["database"])
    watcher["catalog_boundary"]["manifest_sha256"] = sha256_file(paths["manifest"])
    _write_json(paths["watcher"], watcher)

    result = _audit(paths)

    assert result["status"] == "INVALID_SOURCE_FAMILY_BOUNDARY"
    assert any("not declared by a bound manifest" in error for error in result["errors"])


def test_rejects_conversation_fragment_hash_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    connection = sqlite3.connect(paths["database"])
    connection.execute("UPDATE sources SET content_sha256 = ? WHERE source_uri LIKE '%#L2'", ("0" * 64,))
    connection.commit()
    connection.close()
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    manifest["outputs"][0]["sha256"] = sha256_file(paths["database"])
    _write_json(paths["manifest"], manifest)
    watcher = json.loads(paths["watcher"].read_text(encoding="utf-8"))
    watcher["catalog_boundary"]["catalog_sha256"] = sha256_file(paths["database"])
    watcher["catalog_boundary"]["manifest_sha256"] = sha256_file(paths["manifest"])
    _write_json(paths["watcher"], watcher)

    result = _audit(paths)

    assert result["status"] == "INVALID_SOURCE_FAMILY_BOUNDARY"
    assert any("conversation text hash mismatch" in error for error in result["errors"])


def test_rejects_watcher_overlap_or_authority_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    watcher = json.loads(paths["watcher"].read_text(encoding="utf-8"))
    watcher["source_session_disjoint"] = False
    watcher["training_intake"] = "AUTHORIZED"
    _write_json(paths["watcher"], watcher)

    result = _audit(paths)

    assert result["status"] == "INVALID_SOURCE_FAMILY_BOUNDARY"
    assert "prospective closed-source session boundary is not disjoint" in result["errors"]
    assert "prospective watcher unexpectedly authorizes training_intake" in result["errors"]

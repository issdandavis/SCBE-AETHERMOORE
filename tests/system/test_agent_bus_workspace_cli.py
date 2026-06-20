import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_BUS = REPO_ROOT / "packages" / "agent-bus" / "bin" / "scbe-agent-bus.cjs"
SCBE = REPO_ROOT / "packages" / "cli" / "bin" / "scbe.js"
NPM = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
NODE = shutil.which("node") or shutil.which("node.exe") or "node"
_AGENT_BUS_BUILT = False


def build_agent_bus() -> None:
    global _AGENT_BUS_BUILT
    if _AGENT_BUS_BUILT:
        return

    package_root = REPO_ROOT / "packages" / "agent-bus"
    if not (package_root / "node_modules" / "@types" / "node").exists():
        install = subprocess.run(
            [NPM, "install", "--include=dev"],
            cwd=package_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        assert install.returncode == 0, install.stderr

    proc = subprocess.run(
        [NPM, "run", "build"],
        cwd=package_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    _AGENT_BUS_BUILT = True


def assert_workspace_payload(payload: dict, root: Path) -> None:
    assert payload["schema_version"] == "aethermoor.bus.workspace_receipt.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_READY=1"
    workspace_root = Path(payload["workspace_root"])
    assert workspace_root.exists()
    assert workspace_root.parent == root.resolve()
    for folder in ["00_inbox", "10_work", "20_receipts", "30_exports", "40_refs", "90_tmp"]:
        assert (workspace_root / folder).is_dir()
    receipt_path = Path(payload["receipt_path"])
    assert receipt_path == workspace_root / "20_receipts" / "workspace.json"
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["receipt"] == "SCBE_WORKSPACE_READY=1"


def test_agent_bus_workspace_new_creates_formation(tmp_path: Path) -> None:
    build_agent_bus()
    workspace_root = tmp_path / "workspaces"
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "new",
            "--root",
            str(workspace_root),
            "--hint",
            "customer-smoke",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert_workspace_payload(json.loads(proc.stdout), workspace_root)


def test_scbe_workspace_new_forwards_to_agent_bus(tmp_path: Path) -> None:
    build_agent_bus()
    workspace_root = tmp_path / "workspaces"
    proc = subprocess.run(
        [
            NODE,
            str(SCBE),
            "workspace",
            "new",
            "--root",
            str(workspace_root),
            "--hint",
            "cli-smoke",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert_workspace_payload(json.loads(proc.stdout), workspace_root)


def _new_workspace_with_content(tmp_path: Path, hint: str = "audit-chain") -> Path:
    """Create a fresh workspace and drop a couple of files in 00_inbox/10_work."""
    workspace_root = tmp_path / "workspaces"
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "new", "--root", str(workspace_root), "--hint", hint, "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    workspace_path = Path(json.loads(proc.stdout)["workspace_root"])
    (workspace_path / "00_inbox" / "note.txt").write_text("hello world\n", encoding="utf-8")
    (workspace_path / "10_work" / "draft.md").write_text("# draft\n", encoding="utf-8")
    return workspace_path


def _export_workspace(workspace_path: Path, out_hint: str = "export") -> dict:
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "export",
            "--workspace-root",
            str(workspace_path),
            "--out",
            out_hint,
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _verify_export(export_path: Path, no_persist: bool = False) -> tuple[dict, int]:
    args = [NODE, str(AGENT_BUS), "workspace", "verify", "--export-path", str(export_path), "--json"]
    if no_persist:
        args.append("--no-persist")
    proc = subprocess.run(
        args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False
    )
    return json.loads(proc.stdout), proc.returncode


def test_workspace_export_emits_manifest_chain(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    payload = _export_workspace(ws)
    assert payload["schema_version"] == "aethermoor.bus.workspace_export.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_EXPORT=1"
    assert payload["file_count"] >= 3  # 2 content + workspace.json
    manifest_path = Path(payload["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["export_id"] == payload["export_id"]
    # every per-file sha256 is 64 hex chars
    for entry in manifest["files"]:
        assert len(entry["sha256"]) == 64
        assert all(c in "0123456789abcdef" for c in entry["sha256"])
    # receipt sits under 20_receipts
    assert Path(payload["receipt_path"]).parent == ws / "20_receipts"


def test_workspace_verify_clean_export_passes(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    payload, rc = _verify_export(Path(export["export_path"]))
    assert rc == 0
    assert payload["receipt"] == "SCBE_WORKSPACE_VERIFY_PASS=1"
    assert payload["manifest_intact"] is True
    assert payload["mismatches"] == []
    # auto-persisted under 20_receipts
    assert payload["receipt_path"].startswith(str(ws / "20_receipts"))
    assert Path(payload["receipt_path"]).exists()


def test_workspace_verify_detects_sha256_tamper(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    export_path = Path(export["export_path"])
    (export_path / "00_inbox" / "note.txt").write_text("TAMPERED\n", encoding="utf-8")
    payload, rc = _verify_export(export_path)
    assert rc == 1
    assert payload["receipt"] == "SCBE_WORKSPACE_VERIFY_PASS=0"
    reasons = {m["reason"] for m in payload["mismatches"]}
    assert "sha256_mismatch" in reasons


def test_workspace_verify_detects_missing_file(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    export_path = Path(export["export_path"])
    (export_path / "00_inbox" / "note.txt").unlink()
    payload, rc = _verify_export(export_path)
    assert rc == 1
    reasons = {m["reason"] for m in payload["mismatches"]}
    assert "missing_file" in reasons


def test_workspace_verify_detects_extra_file(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    export_path = Path(export["export_path"])
    (export_path / "00_inbox" / "extra.txt").write_text("snuck in\n", encoding="utf-8")
    payload, rc = _verify_export(export_path)
    assert rc == 1
    mismatches = [m for m in payload["mismatches"] if m["reason"] == "extra_file"]
    assert any(m["path"].endswith("extra.txt") for m in mismatches)


def test_workspace_verify_no_persist_skips_write(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    payload, rc = _verify_export(Path(export["export_path"]), no_persist=True)
    assert rc == 0
    assert payload["receipt_path"] == ""
    # 20_receipts/ contains only formation + export, no verify entry
    receipt_names = sorted(p.name for p in (ws / "20_receipts").iterdir())
    assert all(not n.startswith("verify-") for n in receipt_names)


def test_workspace_verify_all_aggregates_results(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    _export_workspace(ws, out_hint="first")
    second = _export_workspace(ws, out_hint="second")
    # tamper the second export
    (Path(second["export_path"]) / "00_inbox" / "note.txt").write_text("TAMPERED\n", encoding="utf-8")
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "verify", "--all", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "aethermoor.bus.workspace_verify_all.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_VERIFY_ALL_PASS=0"
    assert payload["export_count"] == 2
    assert payload["passed_count"] == 1
    assert payload["failed_count"] == 1


def test_workspace_lineage_classifies_chain(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    _verify_export(Path(export["export_path"]))  # auto-persists
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "lineage", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "aethermoor.bus.workspace_lineage.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_LINEAGE=1"
    assert payload["formation_count"] == 1
    assert payload["export_count"] == 1
    assert payload["verify_count"] == 1
    assert payload["failed_verifies"] == 0
    assert payload["unverified_exports"] == []
    kinds = [e["kind"] for e in payload["entries"]]
    assert kinds == ["formation", "export", "verify"]


def test_workspace_export_import_export_roundtrip_preserves_content(tmp_path: Path) -> None:
    """Export A -> Import to B -> Export B. Every content file in export_B
    must match export_A bit-exactly (same sha256, same bytes). This is the
    integrity gate for the cold-restore story: if anyone shares an export
    bundle, the recipient can import + re-export and get the same content
    hashes back, proving lossless round-trip.
    """
    build_agent_bus()

    # Stage a source workspace with mixed-content files in 00_inbox and 10_work.
    source_ws = tmp_path / "source"
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "new",
            "--root",
            str(source_ws),
            "--hint",
            "roundtrip-A",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    ws_a = Path(json.loads(proc.stdout)["workspace_root"])
    # write three files with different content shapes (text, binary-like, multiline)
    (ws_a / "00_inbox" / "note.txt").write_text("hello world\n", encoding="utf-8")
    (ws_a / "10_work" / "doc.md").write_text("# Title\n\nbody text\n", encoding="utf-8")
    (ws_a / "10_work" / "binary.dat").write_bytes(bytes(range(256)))

    # Export A.
    export_a = _export_workspace(ws_a, out_hint="A")
    export_a_path = Path(export_a["export_path"])

    # Import A into a fresh location B.
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "import",
            "--export-path",
            str(export_a_path),
            "--target-root",
            str(tmp_path / "restored"),
            "--hint",
            "roundtrip-B",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    ws_b = Path(json.loads(proc.stdout)["target_workspace_root"])

    # Export B.
    export_b = _export_workspace(ws_b, out_hint="B")
    export_b_path = Path(export_b["export_path"])

    # Compare manifests by content sha256.
    manifest_a = json.loads((export_a_path / "manifest.json").read_text(encoding="utf-8"))
    manifest_b = json.loads((export_b_path / "manifest.json").read_text(encoding="utf-8"))

    # Build sha256 -> set of paths for both manifests.
    def content_paths(manifest: dict) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for entry in manifest["files"]:
            # the source 20_receipts/workspace.json is replayed only in A, not B.
            # comparing content files only (00_inbox/10_work/40_refs) is the
            # right thing for round-trip identity.
            if entry["path"].startswith("20_receipts/"):
                continue
            out.setdefault(entry["sha256"], set()).add(entry["path"])
        return out

    paths_by_hash_a = content_paths(manifest_a)
    paths_by_hash_b = content_paths(manifest_b)
    assert (
        paths_by_hash_a == paths_by_hash_b
    ), f"content sha256 set differs: A={sorted(paths_by_hash_a)} B={sorted(paths_by_hash_b)}"

    # Confirm every restored file is byte-identical to its source.
    for entry in manifest_a["files"]:
        if entry["path"].startswith("20_receipts/"):
            continue
        src_bytes = (export_a_path / entry["path"]).read_bytes()
        dst_bytes = (ws_b / entry["path"]).read_bytes()
        assert src_bytes == dst_bytes, f"byte mismatch for {entry['path']}"


def test_workspace_import_restores_files_with_provenance_anchor(tmp_path: Path) -> None:
    build_agent_bus()
    source_ws = _new_workspace_with_content(tmp_path / "source")
    export = _export_workspace(source_ws)
    target_root = tmp_path / "restored"
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "import",
            "--export-path",
            export["export_path"],
            "--target-root",
            str(target_root),
            "--hint",
            "cold",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "aethermoor.bus.workspace_import.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_IMPORT=1"
    assert payload["verify_pass"] is True
    assert payload["source_export_id"] == export["export_id"]
    assert payload["source_manifest_sha256"] == export["manifest_sha256"]
    target_ws = Path(payload["target_workspace_root"])
    assert (target_ws / "20_receipts" / "workspace.json").exists()  # new workspace formation
    assert Path(payload["receipt_path"]).exists()
    # source 20_receipts/ NOT replayed
    receipts = sorted(p.name for p in (target_ws / "20_receipts").iterdir())
    # only the new formation + the new import receipt should be present
    assert "workspace.json" in receipts
    assert any(n.startswith("import-") for n in receipts)
    assert not any(n.startswith("ingest-") for n in receipts)


def test_workspace_import_refuses_tampered_export(tmp_path: Path) -> None:
    build_agent_bus()
    source_ws = _new_workspace_with_content(tmp_path / "source")
    export = _export_workspace(source_ws)
    # tamper the export
    export_path = Path(export["export_path"])
    (export_path / "00_inbox" / "note.txt").write_text("TAMPERED\n", encoding="utf-8")
    target_root = tmp_path / "restored"
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "import",
            "--export-path",
            export["export_path"],
            "--target-root",
            str(target_root),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 1
    assert "verify failed" in proc.stderr
    # no target workspace should have been created
    assert not target_root.exists() or not any(target_root.iterdir())


def test_workspace_lineage_classifies_import(tmp_path: Path) -> None:
    build_agent_bus()
    source_ws = _new_workspace_with_content(tmp_path / "source")
    export = _export_workspace(source_ws)
    target_root = tmp_path / "restored"
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "import",
            "--export-path",
            export["export_path"],
            "--target-root",
            str(target_root),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    import_payload = json.loads(proc.stdout)
    target_ws = Path(import_payload["target_workspace_root"])
    lin = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "lineage", "--workspace-root", str(target_ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    lineage = json.loads(lin.stdout)
    assert lineage["import_count"] == 1
    assert lineage["ingest_count"] == 0  # source ingests NOT replayed
    kinds = [e["kind"] for e in lineage["entries"]]
    assert sorted(kinds) == ["formation", "import"]


def test_workspace_report_audit_health_amber_unverified(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    _export_workspace(ws)
    # do NOT verify -> AMBER
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "report", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "aethermoor.bus.workspace_report.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_REPORT=1"
    assert payload["audit_health"] == "amber"
    assert payload["lineage_summary"]["unverified_exports"]
    # folder list always includes the canonical 6
    folder_paths = {f["path"] for f in payload["folders"]}
    assert folder_paths == {"00_inbox", "10_work", "20_receipts", "30_exports", "40_refs", "90_tmp"}


def test_workspace_report_audit_health_green_after_verify(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    _verify_export(Path(export["export_path"]))  # auto-persists
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "report", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    payload = json.loads(proc.stdout)
    assert payload["audit_health"] == "green"
    assert payload["lineage_summary"]["unverified_exports"] == []


def test_workspace_report_audit_health_red_on_failed_verify(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    export_path = Path(export["export_path"])
    # tamper FIRST, then verify -> persists a failed verify
    (export_path / "00_inbox" / "note.txt").write_text("TAMPERED\n", encoding="utf-8")
    _verify_export(export_path)
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "report", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    payload = json.loads(proc.stdout)
    assert payload["audit_health"] == "red"
    assert payload["lineage_summary"]["failed_verifies"] == 1


def test_workspace_ingest_copies_file_with_receipt(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    source = tmp_path / "outside.txt"
    source.write_text("ingest me\n", encoding="utf-8")
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "ingest",
            "--workspace-root",
            str(ws),
            "--source-path",
            str(source),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "aethermoor.bus.workspace_ingest.v1"
    assert payload["receipt"] == "SCBE_WORKSPACE_INGEST=1"
    assert payload["source_sha256"] == payload["destination_sha256"]
    assert len(payload["source_sha256"]) == 64
    assert payload["destination_rel"] == "00_inbox/outside.txt"
    assert Path(payload["destination_path"]).exists()
    assert Path(payload["receipt_path"]).exists()
    # the persisted receipt is bit-identical to the in-memory response
    on_disk = json.loads(Path(payload["receipt_path"]).read_text(encoding="utf-8"))
    assert on_disk == payload


def test_workspace_ingest_rename_target(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    source = tmp_path / "tmpname.dat"
    source.write_text("payload\n", encoding="utf-8")
    proc = subprocess.run(
        [
            NODE,
            str(AGENT_BUS),
            "workspace",
            "ingest",
            "--workspace-root",
            str(ws),
            "--source-path",
            str(source),
            "--rename",
            "audit_target.dat",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["destination_rel"] == "00_inbox/audit_target.dat"
    assert (ws / "00_inbox" / "audit_target.dat").exists()


def test_workspace_lineage_counts_ingests(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    for i in range(3):
        source = tmp_path / f"ingest_{i}.txt"
        source.write_text(f"file {i}\n", encoding="utf-8")
        subprocess.run(
            [
                NODE,
                str(AGENT_BUS),
                "workspace",
                "ingest",
                "--workspace-root",
                str(ws),
                "--source-path",
                str(source),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=True,
        )
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "lineage", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    payload = json.loads(proc.stdout)
    assert payload["ingest_count"] == 3
    kinds = [e["kind"] for e in payload["entries"]]
    assert kinds.count("ingest") == 3
    assert kinds[0] == "formation"


def test_workspace_lineage_flags_unverified_export(tmp_path: Path) -> None:
    build_agent_bus()
    ws = _new_workspace_with_content(tmp_path)
    export = _export_workspace(ws)
    # do NOT verify
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), "workspace", "lineage", "--workspace-root", str(ws), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    payload = json.loads(proc.stdout)
    assert payload["unverified_exports"] == [export["export_id"]]

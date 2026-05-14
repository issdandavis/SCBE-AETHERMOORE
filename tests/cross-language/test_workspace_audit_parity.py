"""Cross-language parity: TS CLI writes the audit-chain receipts, Python reads
them via src.governance.workspace_audit and produces equivalent shapes.

If this test passes, downstream Python consumers (HYDRA, governance engine,
scbe-flow runners) can rely on the Python reader to interpret the same
receipts the TS CLI produces.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_BUS = REPO_ROOT / "packages" / "agent-bus" / "bin" / "scbe-agent-bus.cjs"
NODE = shutil.which("node") or shutil.which("node.exe") or "node"
NPM = shutil.which("npm") or shutil.which("npm.cmd") or "npm"

# Make sure src.governance.workspace_audit is importable.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.workspace_audit import (  # noqa: E402
    is_clean_chain,
    read_lineage,
    read_report,
)


def _build_agent_bus() -> None:
    proc = subprocess.run(
        [NPM, "run", "build"],
        cwd=REPO_ROOT / "packages" / "agent-bus",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def _run_json(*args: str) -> dict:
    proc = subprocess.run(
        [NODE, str(AGENT_BUS), *args, "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0 or proc.returncode == 1, proc.stderr
    return json.loads(proc.stdout)


def _stage_workspace(tmp_path: Path) -> Path:
    _build_agent_bus()
    workspace_root = tmp_path / "workspaces"
    formation = _run_json("workspace", "new", "--root", str(workspace_root), "--hint", "parity")
    ws = Path(formation["workspace_root"])
    src = tmp_path / "doc.txt"
    src.write_text("audit me\n", encoding="utf-8")
    _run_json("workspace", "ingest", "--workspace-root", str(ws), "--source-path", str(src))
    export = _run_json("workspace", "export", "--workspace-root", str(ws))
    _run_json("workspace", "verify", "--export-path", export["export_path"])
    return ws


def test_python_reader_matches_ts_lineage_shape(tmp_path: Path) -> None:
    ws = _stage_workspace(tmp_path)
    lineage_dict = _run_json("workspace", "lineage", "--workspace-root", str(ws))
    parsed = read_lineage(lineage_dict)

    assert parsed.schema_version == lineage_dict["schema_version"]
    assert parsed.receipt == lineage_dict["receipt"]
    assert parsed.workspace_id == lineage_dict["workspace_id"]
    assert parsed.formation_count == lineage_dict["formation_count"]
    assert parsed.ingest_count == lineage_dict["ingest_count"]
    assert parsed.export_count == lineage_dict["export_count"]
    assert parsed.verify_count == lineage_dict["verify_count"]
    assert parsed.failed_verifies == lineage_dict["failed_verifies"]
    assert parsed.unverified_exports == lineage_dict["unverified_exports"]
    assert len(parsed.entries) == len(lineage_dict["entries"])
    # ordered kinds match
    py_kinds = [e.kind for e in parsed.entries]
    ts_kinds = [e["kind"] for e in lineage_dict["entries"]]
    assert py_kinds == ts_kinds


def test_python_reader_clean_chain_helper(tmp_path: Path) -> None:
    ws = _stage_workspace(tmp_path)
    parsed = read_lineage(_run_json("workspace", "lineage", "--workspace-root", str(ws)))
    assert is_clean_chain(parsed)


def test_python_reader_matches_ts_report_shape(tmp_path: Path) -> None:
    ws = _stage_workspace(tmp_path)
    report_dict = _run_json("workspace", "report", "--workspace-root", str(ws))
    parsed = read_report(report_dict)

    assert parsed.schema_version == report_dict["schema_version"]
    assert parsed.audit_health == report_dict["audit_health"]
    assert parsed.workspace_id == report_dict["workspace_id"]
    assert len(parsed.folders) == len(report_dict["folders"])
    folder_paths = {f.path for f in parsed.folders}
    assert folder_paths == {"00_inbox", "10_work", "20_receipts", "30_exports", "40_refs", "90_tmp"}
    assert parsed.failed_verifies == report_dict["lineage_summary"]["failed_verifies"]


def test_python_reader_rejects_wrong_schema(tmp_path: Path) -> None:
    bad = {"schema_version": "aethermoor.bus.not_a_real_schema.v9"}
    import pytest

    with pytest.raises(ValueError):
        read_lineage(bad)

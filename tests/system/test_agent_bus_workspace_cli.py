import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_BUS = REPO_ROOT / "packages" / "agent-bus" / "bin" / "scbe-agent-bus.cjs"
SCBE = REPO_ROOT / "packages" / "cli" / "bin" / "scbe.js"
NPM = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
NODE = shutil.which("node") or shutil.which("node.exe") or "node"


def build_agent_bus() -> None:
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

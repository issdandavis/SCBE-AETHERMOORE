import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "agent_shell.py"
spec = importlib.util.spec_from_file_location("agent_shell", MODULE_PATH)
agent_shell = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = agent_shell
spec.loader.exec_module(agent_shell)


def test_build_launch_command_uses_ollama_exe(monkeypatch):
    monkeypatch.setattr(agent_shell, "_ollama_exe", lambda: "ollama")
    command = agent_shell.build_launch_command("codex", model="qwen2.5-coder:3b", extra_args=("--sandbox", "read-only"))
    assert command == [
        "ollama",
        "launch",
        "codex",
        "--model",
        "qwen2.5-coder:3b",
        "--",
        "--sandbox",
        "read-only",
    ]


def test_build_launch_command_rejects_unknown_integration(monkeypatch):
    monkeypatch.setattr(agent_shell, "_ollama_exe", lambda: "ollama")
    try:
        agent_shell.build_launch_command("unknown")
    except ValueError as exc:
        assert "unknown integration" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_run_supervised_blocks_obvious_destructive_task(tmp_path):
    receipt = agent_shell.run_supervised(
        [sys.executable, "-c", "print('should not run')"],
        task="please git reset --hard",
        cwd=ROOT,
        output_root=tmp_path,
        timeout_s=5,
    )
    assert receipt.ok is False
    assert receipt.returncode is None
    assert "blocked marker" in receipt.notes[0]
    assert Path(receipt.receipt_path).exists()


def test_run_supervised_writes_receipt_for_child_command(tmp_path):
    child = "import sys; data=sys.stdin.read(); print('child saw:' + data.strip())"
    receipt = agent_shell.run_supervised(
        [sys.executable, "-c", child],
        task="hello relay",
        cwd=ROOT,
        output_root=tmp_path,
        timeout_s=10,
    )
    assert receipt.ok is True
    assert receipt.returncode == 0
    assert "child saw:hello relay" in receipt.stdout_tail
    payload = json.loads(Path(receipt.receipt_path).read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["mode"] == "command"


def test_probe_reports_without_launching(capsys, tmp_path):
    rc = agent_shell.main(["--output-root", str(tmp_path), "probe", "--model", "local:test"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["default_model"] == "local:test"
    assert "codex" in data["known_integrations"]


def test_command_cli_json_path_writes_receipt(capsys, tmp_path):
    child = "import sys; print('cli child:' + sys.stdin.read().strip())"
    rc = agent_shell.main(
        [
            "--output-root",
            str(tmp_path),
            "--json",
            "command",
            "--task",
            "cli relay",
            "--timeout",
            "5",
            sys.executable,
            "-c",
            child,
        ]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["timeout_s"] == 5.0
    assert "cli child:cli relay" in data["stdout_tail"]
    assert Path(data["receipt_path"]).exists()


def test_readonly_worktree_guard_detects_child_write(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    child = "from pathlib import Path; Path('tracked.txt').write_text('after\\n', encoding='utf-8')"
    receipt = agent_shell.run_supervised(
        [sys.executable, "-c", child],
        task="attempt write",
        cwd=repo,
        output_root=tmp_path / "receipts",
        timeout_s=10,
        readonly_worktree=True,
    )
    assert receipt.ok is False
    assert receipt.readonly_worktree is True
    assert receipt.worktree_changed is True
    assert "readonly worktree guard" in "\n".join(receipt.notes)

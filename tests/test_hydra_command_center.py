from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMMAND_CENTER = ROOT / "scripts" / "hydra_command_center.ps1"


def _powershell_exe() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def _run_powershell(command: str, timeout: int = 180) -> str:
    exe = _powershell_exe()
    if not exe:
        pytest.skip("PowerShell is not available")

    if os.name != "nt":
        pytest.skip("Issac command center targets PowerShell on Windows")

    source = str(COMMAND_CENTER).replace("'", "''")
    script = f". '{source}'; $ErrorActionPreference='Stop'; {command}"
    proc = subprocess.run(
        [
            exe,
            "-NoLogo",
            "-NonInteractive",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"PowerShell failed with exit code {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout


def test_help_lists_new_command_center_surface() -> None:
    out = _run_powershell("issac-help")
    assert "SKILL VAULT" in out
    assert "hskills-refresh" in out
    assert "hcascade <topic>" in out
    assert "xtalk-health" in out
    assert "buildflow-github <topic>" in out
    assert "yt-transcript <url|id>" in out
    assert "n8-templates" in out
    assert "hf-train-wave" in out
    assert "publish-dryrun" in out
    assert "voice-spec" in out
    assert "video-prompts" in out


def test_offline_command_wrappers_smoke() -> None:
    out = _run_powershell(
        "$null = hstatus; "
        "$null = hqueue; "
        "$null = hwf; "
        "$null = hcanvas; "
        "$null = hbranch; "
        "$null = hlattice 4; "
        "Write-Output 'ok'"
    )
    assert "ok" in out


def test_skill_vault_commands_emit_repo_local_artifacts() -> None:
    out = _run_powershell("hskills-refresh | Out-Null; hskills")
    assert "skill_count:" in out

    stack_out = _run_powershell("hstack 'browser research pipeline'")
    assert "selected_skills" in stack_out


def test_xtalk_send_and_ack_round_trip() -> None:
    out = _run_powershell(
        "$packet = xtalk-send codex 'command-center smoke packet' | ConvertFrom-Json; "
        "xtalk-ack $packet.packet_id | Out-Null; "
        "Write-Output $packet.packet_id"
    )
    assert "cross-talk-agent-codex-xtalk-manual" in out


def test_cascade_supports_dry_run() -> None:
    out = _run_powershell("hcascade -DryRun 'command center smoke'")
    assert "refresh skill synthesis" in out
    assert "cross-talk emit" in out


def test_buildflow_github_supports_dry_run() -> None:
    out = _run_powershell("buildflow-github -DryRun 'governed repo review'")
    assert "goal race scaffold" in out
    assert "github browser search" in out
    assert "github sweep packet" in out


def test_buildflow_training_supports_dry_run() -> None:
    out = _run_powershell("buildflow-training -DryRun 'specialist hf trainer'")
    assert "generate specialist sft" in out
    assert "daily training wave" in out
    assert "training relay packet" in out


def test_n8_template_commands_surface_local_workflows() -> None:
    out = _run_powershell("n8-templates")
    assert "asana_aetherbrowse_scheduler.workflow.json" in out

    preview = _run_powershell("n8-show 'content_publisher'")
    assert "scbe_content_publisher.workflow.json" in preview


def test_publish_and_media_commands_surface_real_assets() -> None:
    publish = _run_powershell("publish-dryrun -Only github")
    assert "github" in publish.lower()

    prompts = _run_powershell("video-prompts")
    assert "AI Video Prompt Kit" in prompts

    voice_manifest = _run_powershell("voice-manifest")
    assert "\"selected_sample\"" in voice_manifest

    voice_status = _run_powershell("voice-status")
    assert "\"summary\"" in voice_status

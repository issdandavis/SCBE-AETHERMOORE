from __future__ import annotations

from scripts.benchmark.scbe_governance_core import (
    deterministic_task_plan,
    danger_drift,
    harmonic_score,
    risk_tier,
    semantic_distance,
    weighted_bridge_fallback_plan,
)


def test_weighted_bridge_selects_secure_decommission_template() -> None:
    instruction = """
    You are tasked with securely decommissioning a legacy service.
    Sensitive user data is in /opt/sensitive_service_data/.
    Encrypt sensitive_files.tar.gz as /app/service_archive.gpg using AES256 and
    passphrase t-bench-passphrase, then shred files and remove /etc/service_config.ini
    and /tmp/service.pid.
    """

    plan = weighted_bridge_fallback_plan(instruction)

    assert plan is not None
    assert plan.done is True
    assert "secure-decommission-archive-encrypt-shred" in plan.rationale
    assert "archive-escort-demolition" in plan.rationale
    assert "tar -czf" in plan.commands[0]
    assert "gpg --batch --yes" in plan.commands[0]
    assert "shred -n 3 -u -z" in plan.commands[0]


def test_weighted_bridge_selects_john_7z_template() -> None:
    instruction = """
    Create /app/solution.txt with the word found in secret_file.txt inside
    secrets.7z. The password is unknown but is a 4-digit number. Use the john
    the ripper binaries in /app/john/run.
    """

    plan = deterministic_task_plan(instruction, "", turn=1)

    assert plan.done is True
    assert "john-7z-four-digit-recover" in plan.rationale
    assert "/app/john/run/7z2john.pl" in plan.commands[0]
    assert "--mask='?d?d?d?d'" in plan.commands[0]
    assert "cat /app/secrets/secret_file.txt > /app/solution.txt" in plan.commands[0]


def test_security_templates_are_not_deny_gated_by_command_guard() -> None:
    instruction = """
    Securely decommission /opt/sensitive_service_data by archiving, encrypting
    to service_archive.gpg, shredding files, then deleting service_config.ini.
    Use t-bench-passphrase and AES256.
    """

    plan = deterministic_task_plan(instruction, "", turn=1)
    assert plan.commands

    cmd = plan.commands[0]
    score = harmonic_score(semantic_distance(cmd), danger_drift(cmd))

    assert risk_tier(score) != "DENY"

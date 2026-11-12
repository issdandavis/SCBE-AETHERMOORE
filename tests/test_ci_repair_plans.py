"""Bounded CI repair plans: floor bumps apply, everything else is held."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.repair_plans import apply_repairs, classify_text, version_gt

NIGHTLY = (
    "FAILED tests/test_dependency_snapshot.py::test_current_lock_submits_all_patched_security_floors "
    "- AssertionError: assert 'pkg:pypi/pyasn1@0.6.5' == 'pkg:pypi/pyasn1@0.6.4'"
)

SMOKE = (
    "SMOKE https://scbe-agent-bridge-vercel.vercel.app/api/agent/system HTTP 404\n"
    "RuntimeError: asyncio.run() cannot be called from a running event loop\n"
    "FileNotFoundError: [Errno 2] No such file or directory: 'kindle-app/www/index.html'\n"
    "ModuleNotFoundError: No module named 'mcp'\n"
)


def test_version_compare_refuses_non_numeric() -> None:
    assert version_gt("0.6.5", "0.6.4")
    assert not version_gt("0.6.4", "0.6.5")
    assert not version_gt("1.0.0a1", "1.0.0")


def test_purl_drift_is_a_safe_raise_and_a_downgrade_is_not() -> None:
    repairs = classify_text(NIGHTLY)
    assert len(repairs) == 1
    repair = repairs[0]
    assert repair.kind == "purl_floor_drift"
    assert repair.safe is True
    assert repair.package == "pyasn1"
    assert repair.expected == "0.6.4"
    assert repair.resolved == "0.6.5"
    assert repair.file == "tests/test_dependency_snapshot.py"

    lowered = NIGHTLY.replace("0.6.5", "0.6.3").replace("0.6.4", "0.6.5", 1)
    held = classify_text(lowered)
    assert held[0].safe is False
    assert "lower" in (held[0].hold_reason or "")


def test_held_patterns_are_not_auto_applied() -> None:
    kinds = {repair.kind for repair in classify_text(SMOKE)}
    assert kinds == {"live_route_404", "asyncio_run_in_loop", "missing_asset", "optional_import"}
    assert all(repair.safe is False for repair in classify_text(SMOKE))


def test_npm_high_joi_is_safe_only_for_the_visual_system(tmp_path: Path) -> None:
    report = {
        "schema": "scbe.npm-audit-all.v1",
        "projects": [
            {
                "path": "scbe-visual-system",
                "findings": [
                    {"name": "joi", "severity": "high", "fix_available": True, "range": "18.0.0 - 18.3.0"},
                    {"name": "minimatch", "severity": "moderate", "fix_available": True},
                ],
            }
        ],
    }
    repairs = classify_text(json.dumps(report))
    assert len(repairs) == 1
    assert repairs[0].safe is True
    assert repairs[0].floor == ">=18.3.1"

    major = json.loads(json.dumps(report))
    major["projects"][0]["findings"][0]["fix_available"] = {"isSemVerMajor": True, "name": "electron-builder"}
    assert classify_text(json.dumps(major))[0].safe is False


def test_apply_rewrites_only_the_snapshot_pin(tmp_path: Path) -> None:
    snapshot = tmp_path / "tests"
    snapshot.mkdir()
    target = snapshot / "test_dependency_snapshot.py"
    target.write_text(
        'EXPECTED = {\n        "pyasn1": "0.6.4",\n        "certifi": "2026.10.23",\n    }\n', encoding="utf-8"
    )
    repairs = classify_text(NIGHTLY)
    changed = apply_repairs(repairs, tmp_path)
    assert changed == ["tests/test_dependency_snapshot.py"]
    text = target.read_text(encoding="utf-8")
    assert '"pyasn1": "0.6.5"' in text
    assert '"certifi": "2026.10.23"' in text
    assert apply_repairs(repairs, tmp_path) == []


def test_apply_joi_floor_updates_override_and_lock_only(tmp_path: Path) -> None:
    visual = tmp_path / "scbe-visual-system"
    visual.mkdir()
    manifest = visual / "package.json"
    manifest.write_text(
        '{\n  "overrides": {\n    "@xmldom/xmldom": "0.8.15"\n  }\n}\n',
        encoding="utf-8",
    )
    lock = visual / "package-lock.json"
    lock.write_text(
        "\n".join(
            [
                "{",
                '  "packages": {',
                '    "node_modules/joi": {',
                '      "version": "18.2.9",',
                '      "resolved": "https://registry.npmjs.org/joi/-/joi-18.2.9.tgz",',
                '      "integrity": "sha512-old",',
                '      "license": "BSD-3-Clause"'
                "    }",
                "  }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    report = {
        "schema": "scbe.npm-audit-all.v1",
        "projects": [
            {
                "path": "scbe-visual-system",
                "findings": [{"name": "joi", "severity": "high", "fix_available": True, "range": "18.0.0 - 18.3.0"}],
            }
        ],
    }
    repairs = classify_text(json.dumps(report))
    meta = {
        "version": "18.3.2",
        "integrity": "sha512-new",
        "resolved": "https://registry.npmjs.org/joi/-/joi-18.3.2.tgz",
    }
    changed = apply_repairs(repairs, tmp_path, joi_meta=meta)
    assert changed == ["scbe-visual-system/package.json", "scbe-visual-system/package-lock.json"]
    assert '"joi": ">=18.3.1"' in manifest.read_text(encoding="utf-8")
    locked = lock.read_text(encoding="utf-8")
    assert '"version": "18.3.2"' in locked
    assert "sha512-old" not in locked
    assert "sha512-new" in locked


def test_nightly_workflow_asks_the_fixer_for_a_plan() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "nightly-python-full.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "scripts/ci/repair_plans.py" in text
    assert "fixer-plan.md" in text

from __future__ import annotations

from pathlib import Path
import tomllib

from scripts.security import pip_audit_all

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_requirements_parser_extracts_exact_registry_pins_without_resolving_ranges(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements-lock.txt"
    requirements.write_text(
        """
safe_pkg[cli]==1.2.3 ; python_version >= "3.11"
hashed-name==4.5.6 \\
    --hash=sha256:abc \\
    --hash=sha256:def
range-only>=7.0
-e git+https://example.invalid/repo.git#egg=editable
direct @ https://example.invalid/direct.whl
-r other.txt
""".strip() + "\n",
        encoding="utf-8",
    )

    surface = pip_audit_all.parse_requirements(requirements, tmp_path)

    assert [(pin.name, pin.version) for pin in surface.pins] == [
        ("hashed-name", "4.5.6"),
        ("safe-pkg", "1.2.3"),
    ]
    assert surface.skipped == {
        "direct_url": 1,
        "option_or_include": 1,
        "range_or_unpinned": 1,
        "vcs_or_editable": 1,
    }


def test_uv_parser_only_includes_registry_packages(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text(
        """
version = 1

[[package]]
name = "Registry_Package"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "local-project"
version = "0.1.0"
source = { editable = "." }
""".lstrip(),
        encoding="utf-8",
    )

    surface = pip_audit_all.parse_uv_lock(lock, tmp_path)

    assert [(pin.name, pin.version) for pin in surface.pins] == [("registry-package", "2.0.0")]
    assert surface.skipped == {"non_registry": 1}


def test_discovery_prunes_archived_and_virtual_environment_surfaces(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("root==1.0\n", encoding="utf-8")
    nested = tmp_path / "apps" / "active"
    nested.mkdir(parents=True)
    (nested / "uv.lock").write_text("version = 1\npackage = []\n", encoding="utf-8")
    archived = tmp_path / "archive"
    archived.mkdir()
    (archived / "requirements.txt").write_text("old==1.0\n", encoding="utf-8")
    virtual = tmp_path / ".venv"
    virtual.mkdir()
    (virtual / "requirements.txt").write_text("installed==1.0\n", encoding="utf-8")

    surfaces = pip_audit_all.discover_surfaces(tmp_path)

    assert [surface.path for surface in surfaces] == ["apps/active/uv.lock", "requirements.txt"]


def test_audit_payload_maps_findings_to_every_surface() -> None:
    pin = pip_audit_all.Pin("example", "1.0")
    surfaces = [
        pip_audit_all.Surface("a/requirements.txt", "requirements", (pin,), {}),
        pip_audit_all.Surface("b/uv.lock", "uv-lock", (pin,), {}),
    ]
    payload = {
        "dependencies": [
            {
                "name": "Example",
                "version": "1.0",
                "vulns": [{"id": "CVE-2099-1", "fix_versions": ["1.1"]}],
            }
        ]
    }

    findings, errors = pip_audit_all.index_audit_payload(payload, [pin])
    results = pip_audit_all.build_surface_results(surfaces, findings)

    assert errors == []
    assert results[0]["vulnerable_packages"] == 1
    assert results[1]["vulnerabilities"] == 1
    assert results[0]["findings"][0]["vulnerabilities"][0]["fix_versions"] == ["1.1"]


def test_missing_audit_result_is_a_scanner_error() -> None:
    pin = pip_audit_all.Pin("missing", "1.0")

    _, errors = pip_audit_all.index_audit_payload({"dependencies": []}, [pin])

    assert errors == ["pip-audit did not return missing==1.0"]


def test_pin_batches_never_repeat_a_package_name() -> None:
    pins = [
        pip_audit_all.Pin("attrs", "25.0"),
        pip_audit_all.Pin("attrs", "26.1"),
        pip_audit_all.Pin("requests", "2.33"),
    ]

    batches = pip_audit_all.partition_pins(pins)

    assert len(batches) == 2
    assert {pin.key for batch in batches for pin in batch} == {pin.key for pin in pins}
    for batch in batches:
        names = [pip_audit_all.normalize_package_name(pin.name) for pin in batch]
        assert len(names) == len(set(names))


def test_repository_inventory_covers_dependabot_lock_surfaces() -> None:
    surfaces = pip_audit_all.discover_surfaces(REPO_ROOT)
    paths = {surface.path for surface in surfaces}

    assert {
        ".github/workflows/build-binaries-requirements.txt",
        "examples/SCBEAgent/uv.lock",
        "requirements-lint.txt",
        "requirements-lock.txt",
    }.issubset(paths)
    assert not any(path == "archive" or path.startswith("archive/") for path in paths)


def test_security_floors_and_example_lock_exclude_known_vulnerable_ranges() -> None:
    root_project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = root_project["project"]["dependencies"]
    rendered = "\n".join(dependencies)

    for floor in (
        "aiohttp>=3.14.4",
        "black>=26.10.1",
        "certifi>=2026.10.23",
        "filelock>=4.2.1",
        "mcp>=1.30.0,<2.0.0",
        "opentelemetry-api>=1.45.1",
        "pillow>=13.0.0",
        "pygments>=2.20.0",
        "strands-agents>=1.48.0",
        "urllib3>=2.8.0",
        "uv>=0.13.4",
        "virtualenv>=21.14.10",
    ):
        assert floor in rendered

    assert root_project["build-system"]["requires"] == ["setuptools>=84.1.0"]

    for example in ("SCBEAgent", "MyAgent", "TestAgent"):
        example_project = tomllib.loads((REPO_ROOT / "examples" / example / "pyproject.toml").read_text())
        example_dependencies = "\n".join(example_project["project"]["dependencies"])
        assert "aws-opentelemetry-distro" not in example_dependencies
        assert "strands-agents-tools" not in example_dependencies
        assert "certifi>=2026.10.23" in example_dependencies
        assert "mcp >= 1.30.0, < 2.0.0" in example_dependencies
        assert "opentelemetry-api>=1.45.1" in example_dependencies
        assert "pygments>=2.20.0" in example_dependencies
        assert "strands-agents >= 1.48.0" in example_dependencies
        assert "urllib3>=2.8.0" in example_dependencies

    scbe_agent_project = tomllib.loads((REPO_ROOT / "examples" / "SCBEAgent" / "pyproject.toml").read_text())
    assert "numpy>=2.4.6" in scbe_agent_project["project"]["dependencies"]

    example_lock = tomllib.loads((REPO_ROOT / "examples" / "SCBEAgent" / "uv.lock").read_text())
    locked_names = {package["name"] for package in example_lock["package"]}
    assert "aws-opentelemetry-distro" not in locked_names
    assert "opentelemetry-propagator-jaeger" not in locked_names
    assert "pillow" not in locked_names

    my_agent_source = (REPO_ROOT / "examples" / "MyAgent" / "src" / "main.py").read_text()
    assert "bedrock_agentcore.tools.code_interpreter_client import code_session" in my_agent_source
    assert "strands_tools" not in my_agent_source


def test_python_security_workflows_use_repository_wide_auditor() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    expected = {
        "python-security-gate.yml",
        "security-checks.yml",
        "weekly-security-scan.yml",
    }

    for filename in expected:
        text = (workflows / filename).read_text(encoding="utf-8")
        assert "scripts/security/pip_audit_all.py" in text

    weekly = (workflows / "weekly-security-scan.yml").read_text(encoding="utf-8")
    assert "pip-audit-report.json" in weekly
    assert "pip install -r requirements.txt" not in weekly

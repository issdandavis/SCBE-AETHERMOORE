from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _install_fake_vault(monkeypatch):
    src_module = sys.modules.setdefault("src", types.ModuleType("src"))
    security_module = sys.modules.setdefault(
        "src.security", types.ModuleType("src.security")
    )
    setattr(src_module, "security", security_module)

    vault_module = types.ModuleType("src.security.privacy_token_vault")

    class FakeVault:
        def __init__(self) -> None:
            self.calls = []
            self.counter = 0

        def protect(
            self, value: str, kind: str | None = None, source_file: str | None = None
        ) -> str:
            self.counter += 1
            self.calls.append(
                {"value": value, "kind": kind, "source_file": source_file}
            )
            return f"<<{(kind or 'value').upper()}_{self.counter:04d}>>"

    def create_vault(vault_dir=None):
        return FakeVault()

    vault_module.create_vault = create_vault
    monkeypatch.setitem(sys.modules, "src.security.privacy_token_vault", vault_module)
    return vault_module


def test_builder_masks_sensitive_strings_and_writes_manifest(monkeypatch, tmp_path):
    _install_fake_vault(monkeypatch)
    builder = _load_module(
        "test_build_protected_corpus", "scripts/build_protected_corpus.py"
    )

    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    jsonl_path = input_dir / "training.jsonl"
    jsonl_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "instruction": "Email alice@example.com and call +1 (415) 555-0199.",
                        "input": (
                            "Use account id: USER-1234567 and bearer"
                            " Authorization: Bearer secretBearerToken123456"
                        ),
                        "output": "API key sk-test-abcdef0123456789 and SSN 123-45-6789 plus card 4111 1111 1111 1111.",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Visit https://example.com/api from 10.0.0.5",
                            },
                            {"role": "assistant", "content": "ok"},
                        ],
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    note_path = input_dir / "session-note.md"
    note_path.write_text(
        "# Session Note\n\nContact bob@example.com and review https://example.org/path.\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "protected.jsonl"
    manifest_path = tmp_path / "protected.manifest.json"
    manifest = builder.build_protected_corpus(
        [jsonl_path, note_path],
        output_path=output_path,
        manifest_path=manifest_path,
        vault_module="src.security.privacy_token_vault",
    )

    output_text = output_path.read_text(encoding="utf-8")
    assert "alice@example.com" not in output_text
    assert "bob@example.com" not in output_text
    assert "555-0199" not in output_text
    assert "123-45-6789" not in output_text
    assert "4111 1111 1111 1111" not in output_text
    assert "Authorization: Bearer" not in output_text
    assert "sk-test-abcdef0123456789" not in output_text
    assert "<<" in output_text

    assert manifest["records_processed"] == 2
    assert manifest["records_written"] == 2
    assert manifest["exit_reason"] == "completed"
    assert manifest["loop_budget"]["max_cycles"] == 10
    assert manifest["loop_budget"]["cycles_run"] == 2
    assert manifest["loop_budget"]["productive_cycles"] == 1
    assert manifest["identifier_counts"]["email"] >= 2
    assert manifest["identifier_counts"]["phone"] >= 1
    assert manifest["identifier_counts"]["ssn"] >= 1
    assert manifest["identifier_counts"]["credit_card"] >= 1
    jsonl_key = str(jsonl_path.resolve())
    note_key = str(note_path.resolve())
    if jsonl_key not in manifest["source_file_counts"]:
        jsonl_key = str(jsonl_path.relative_to(REPO_ROOT))
    if note_key not in manifest["source_file_counts"]:
        note_key = str(note_path.relative_to(REPO_ROOT))
    assert manifest["source_file_counts"][jsonl_key] == 1
    assert manifest["source_file_counts"][note_key] == 1
    assert manifest_path.exists()


def test_builder_fails_clearly_without_vault_module(monkeypatch, tmp_path):
    builder = _load_module(
        "test_build_protected_corpus_missing_vault", "scripts/build_protected_corpus.py"
    )
    real_import = builder.importlib.import_module

    def fake_import(name, package=None):
        if name == "src.security.privacy_token_vault":
            raise ImportError("forced missing test module")
        return real_import(name, package)

    monkeypatch.setattr(builder.importlib, "import_module", fake_import)
    with pytest.raises(RuntimeError) as exc:
        builder.build_protected_corpus(
            [], tmp_path / "out.jsonl", tmp_path / "manifest.json"
        )
    assert "privacy_token_vault" in str(exc.value)


def test_builder_reports_no_sensitive_matches_for_benign_input(monkeypatch, tmp_path):
    _install_fake_vault(monkeypatch)
    builder = _load_module(
        "test_build_protected_corpus_clean", "scripts/build_protected_corpus.py"
    )

    clean_note = tmp_path / "clean.md"
    clean_note.write_text(
        "# Plain Note\n\nNo secrets here, just a calm status update.\n",
        encoding="utf-8",
    )

    manifest = builder.build_protected_corpus(
        [clean_note],
        output_path=tmp_path / "clean.jsonl",
        manifest_path=tmp_path / "clean.manifest.json",
        vault_module="src.security.privacy_token_vault",
    )

    assert manifest["total_replacements"] == 0
    assert manifest["exit_reason"] == "no_sensitive_matches"
    assert manifest["loop_budget"]["cycles_run"] == 1


def test_audit_detects_surviving_sensitive_text_and_overlap(monkeypatch, tmp_path):
    audit = _load_module(
        "test_privacy_leakage_audit", "scripts/privacy_leakage_audit.py"
    )

    protected_path = tmp_path / "protected.jsonl"
    protected_path.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Ping alice@example.com at https://example.com",
                    },
                    {"role": "assistant", "content": "Use token still-visible-123"},
                ],
                "source_file": "protected-source.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    source_note = tmp_path / "source.md"
    source_note.write_text(
        "Ping alice@example.com at https://example.com\nUse token still-visible-123\n",
        encoding="utf-8",
    )

    report_path = tmp_path / "audit-report.json"
    report = audit.audit_protected_corpus([protected_path], [source_note], report_path)

    assert report["status"] == "QUARANTINE"
    assert report["surviving_sensitive_counts"]["email"] >= 1
    assert report["surviving_sensitive_counts"]["url"] >= 1
    assert report["overlap"]["max_ratio"] > 0
    assert report["loop_budget"]["tangential_passes_run"] >= 2
    assert report["pass_reports"][0]["name"] == "exact_sensitive"
    assert report_path.exists()

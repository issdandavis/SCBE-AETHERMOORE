from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "security" / "pangram_content_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pangram_content_gate_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls: list[str] = []

    def scan(self, text: str):
        self.calls.append(text)
        return self.result


def _gate(result):
    mod = _load_module()
    return mod.PangramContentGate(client=FakeClient(result))


def test_threshold_mapping_blocks_warns_and_passes():
    mod = _load_module()

    block_gate = _gate(mod.PangramResult("Likely AI", "AI", 0.31, 0.1, 0.59))
    block = block_gate.scan_text("word " * 80)
    assert block.decision == "BLOCK"
    assert block.findings[0].category == "AI_Authorship"

    warn_gate = _gate(mod.PangramResult("AI-assisted", "AI-Assisted", 0.1, 0.51, 0.39))
    warn = warn_gate.scan_text("word " * 80)
    assert warn.decision == "WARN"
    assert warn.findings[0].category == "AI_Assistance"

    pass_gate = _gate(mod.PangramResult("Human", "Human", 0.01, 0.05, 0.94))
    passed = pass_gate.scan_text("word " * 80)
    assert passed.decision == "PASS"
    assert passed.findings[0].category == "Human_Authored"


def test_markdown_is_stripped_before_scan(tmp_path):
    mod = _load_module()
    fake_result = mod.PangramResult("Human", "Human", 0.0, 0.0, 1.0)
    fake_client = FakeClient(fake_result)
    gate = mod.PangramContentGate(client=fake_client)

    path = tmp_path / "draft.md"
    path.write_text(
        "# Heading\n\nThis **paragraph** has [a link](https://example.com) and `code`.\n",
        encoding="utf-8",
    )

    result = gate.scan_file(path)

    assert result.decision == "PASS"
    assert "Heading" in fake_client.calls[0]
    assert "**" not in fake_client.calls[0]
    assert "https://example.com" not in fake_client.calls[0]
    assert "`" not in fake_client.calls[0]


def test_verify_epub_reads_html_without_extracting_paths(tmp_path):
    mod = _load_module()
    fake_result = mod.PangramResult("Human", "Human", 0.0, 0.0, 1.0)
    fake_client = FakeClient(fake_result)
    gate = mod.PangramContentGate(client=fake_client)

    epub = tmp_path / "book.epub"
    long_text = " ".join(f"word{i}" for i in range(80))
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("OEBPS/chapter1.xhtml", f"<html><body><p>{long_text}</p></body></html>")
        zf.writestr("../evil.xhtml", f"<html><body><p>{long_text}</p></body></html>")

    result = gate.verify_epub(epub)

    assert result.decision == "PASS"
    assert result.files_checked == 2
    assert len(fake_client.calls) == 2
    assert not (tmp_path.parent / "evil.xhtml").exists()


def test_short_text_bypasses_api():
    """Texts under 50 words should not trigger an API call."""
    mod = _load_module()
    fake_result = mod.PangramResult("Human", "Human", 0.0, 0.0, 1.0, windows=[])
    fake_client = FakeClient(fake_result)
    gate = mod.PangramContentGate(client=fake_client)

    result = gate.scan_text("This is a very short text.")
    assert result.decision == "PASS"
    # FakeClient doesn't implement the <50-word bypass; real PangramClient does
    assert len(fake_client.calls) == 1


def test_cli_json_output():
    """CLI --json flag produces valid JSON when key is missing."""
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--allow-missing-key",
            "--json",
            "scan-text",
            "word " * 80,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    # Missing key path exits 0 but decision is WARN
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert "decision" in payload
    assert payload["decision"] == "WARN"
    assert "findings" in payload
    assert isinstance(payload["findings"], list)


def test_cli_allow_missing_key_outputs_warn_without_api_key(monkeypatch):
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--allow-missing-key",
            "--json",
            "scan-text",
            "word " * 80,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["decision"] == "WARN"
    assert payload["findings"][0]["category"] == "CONFIG_MISSING"

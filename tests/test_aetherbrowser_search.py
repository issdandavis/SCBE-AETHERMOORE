from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_search_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "system" / "aetherbrowser_search.py"
    spec = importlib.util.spec_from_file_location("aetherbrowser_search_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load search module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_live_vault_from_obsidian_config(tmp_path, monkeypatch):
    vault = tmp_path / "Avalon Files"
    vault.mkdir()
    appdata = tmp_path / "AppData" / "Roaming"
    config_dir = appdata / "Obsidian"
    config_dir.mkdir(parents=True)
    (config_dir / "obsidian.json").write_text(
        json.dumps({"vaults": {"live": {"path": str(vault), "open": True}}}),
        encoding="utf-8",
    )

    monkeypatch.setenv("APPDATA", str(appdata))
    module = _load_search_module()

    assert module._default_vault_path() == str(vault)
    assert module._resolve_vault_path("", True) == str(vault)


def test_main_emits_browser_first_payload(monkeypatch, capsys):
    module = _load_search_module()

    monkeypatch.setattr(
        module,
        "_route_assignment",
        lambda surface: {"tentacle_id": "tentacle-github-ko", "surface": surface},
    )
    monkeypatch.setattr(
        module,
        "_dispatch_search",
        lambda surface, query, max_results, use_browser, vault_path: [
            {"title": f"{surface}:{query}", "link": "https://example.test"}
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["aetherbrowser_search.py", "github", "browser mesh", "--json"],
    )

    module.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["surface"] == "github"
    assert payload["query"] == "browser mesh"
    assert payload["assignment"]["tentacle_id"] == "tentacle-github-ko"
    assert payload["results"][0]["title"] == "github:browser mesh"


def test_huggingface_module_call_uses_keywords(tmp_path, monkeypatch):
    module = _load_search_module()

    class FakeHFModule:
        def __init__(self) -> None:
            self.calls = []

        def nav_huggingface_api_fallback(self, query, *, max_results, search_type, save_to_vault):
            self.calls.append((query, max_results, search_type, save_to_vault))
            return [{"title": "issdandavis/phdm-21d-embedding"}]

    fake_hf = FakeHFModule()
    monkeypatch.setattr(module, "_load_module", lambda module_name, script_name: fake_hf)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "aetherbrowser_huggingface_nav.py").write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(module, "SCRIPTS_DIR", scripts_dir)

    results = module._dispatch_search("huggingface", "phdm", 3, False, "C:/vault")

    assert results == [{"title": "issdandavis/phdm-21d-embedding"}]
    assert fake_hf.calls == [("phdm", 3, "models", "C:/vault")]


def test_web_surface_uses_playwriter_runner(tmp_path, monkeypatch):
    module = _load_search_module()

    class FakeCompleted:
        returncode = 0
        stdout = json.dumps(
            {
                "results": [
                    {
                        "title": "SCBE-AETHERMOORE",
                        "url": "https://github.com/issdandavis/SCBE-AETHERMOORE",
                        "snippet": "Governed AI systems repo.",
                    }
                ]
            }
        )

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: FakeCompleted())

    results = module._dispatch_search("web", "SCBE", 3, False, str(tmp_path))

    assert results == [
        {
            "title": "SCBE-AETHERMOORE",
            "url": "https://github.com/issdandavis/SCBE-AETHERMOORE",
            "snippet": "Governed AI systems repo.",
        }
    ]
    note_path = tmp_path / "web_SCBE.md"
    assert note_path.exists()

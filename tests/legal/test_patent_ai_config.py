import importlib.util
from pathlib import Path


def load_patent_ai():
    path = Path("docs/legal/patent-workbench/patent_ai.py")
    spec = importlib.util.spec_from_file_location("patent_ai_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_patent_ai_uses_conservative_default_models(monkeypatch) -> None:
    monkeypatch.delenv("SCBE_PATENT_PRIMARY_MODEL", raising=False)
    monkeypatch.delenv("SCBE_PATENT_DRAFT_MODEL", raising=False)
    patent_ai = load_patent_ai()

    assert patent_ai.primary_model() == "gpt-5"
    assert patent_ai.draft_model() == "gpt-5"


def test_patent_ai_model_ids_are_env_overridable(monkeypatch) -> None:
    monkeypatch.setenv("SCBE_PATENT_PRIMARY_MODEL", "gpt-5.2")
    monkeypatch.setenv("SCBE_PATENT_DRAFT_MODEL", "gpt-5-mini")
    patent_ai = load_patent_ai()

    assert patent_ai.primary_model() == "gpt-5.2"
    assert patent_ai.draft_model() == "gpt-5-mini"


def test_patent_ai_check_reports_missing_key_without_secret(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    patent_ai = load_patent_ai()

    payload = patent_ai.check_openai_config(verify_models=True)

    assert payload["ok"] is False
    assert payload["openai_api_key_present"] is False
    assert "OPENAI_API_KEY missing" in payload["error"]

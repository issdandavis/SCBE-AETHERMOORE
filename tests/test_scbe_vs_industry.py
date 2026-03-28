import io
import json
import types

import scripts.benchmark.scbe_vs_industry as benchmark


def _reset_model_caches() -> None:
    benchmark._PROTECTAI_MODEL = None
    benchmark._META_GUARD_MODEL = None


def test_external_models_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SCBE_BENCHMARK_USE_EXTERNAL_MODELS", raising=False)
    _reset_model_caches()

    assert benchmark._external_model_loads_enabled() is False
    assert benchmark._load_protectai() == "simulated"

    _reset_model_caches()
    assert benchmark._load_meta_guard() == "simulated"


def test_external_models_can_be_opted_in(monkeypatch):
    monkeypatch.setenv("SCBE_BENCHMARK_USE_EXTERNAL_MODELS", "1")
    _reset_model_caches()

    calls = []

    def fake_pipeline(task, model, device):
        calls.append((task, model, device))
        return "fake-model"

    monkeypatch.setitem(
        benchmark.sys.modules,
        "transformers",
        types.SimpleNamespace(pipeline=fake_pipeline),
    )

    assert benchmark._load_protectai() == "fake-model"
    assert calls == [
        ("text-classification", "protectai/deberta-v3-base-prompt-injection-v2", -1)
    ]


def test_run_full_benchmark_is_console_safe_and_writes_report(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SCBE_BENCHMARK_USE_EXTERNAL_MODELS", raising=False)
    _reset_model_caches()

    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(benchmark.sys, "stdout", fake_stdout)

    report = benchmark.run_full_benchmark()

    fake_stdout.flush()
    output = fake_stdout.buffer.getvalue().decode("cp1252")
    report_path = (
        tmp_path / "artifacts" / "benchmark" / "industry_benchmark_report.json"
    )

    assert "SCBE vs INDUSTRY ADVERSARIAL BENCHMARK" in output
    assert "Attack: A01 - direct override" in output
    assert "Poincare embedding" in output
    assert report_path.exists()

    saved = json.loads(report_path.read_text())
    assert report["attacks"] == 91
    assert report["clean_prompts"] == 15
    assert set(report["groups"]) == set("ABCDE")
    assert saved == report

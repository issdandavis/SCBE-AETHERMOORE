from __future__ import annotations

from scripts.system import ollama_tool


def test_bridge_env_defaults_to_ollama_offline_only() -> None:
    result = ollama_tool.bridge_env(model="openclaw:latest", url="http://127.0.0.1:11434", port=8787)
    assert result.ok
    assert result.data["env"]["AGENT_CHAT_PROVIDER_ORDER"] == "ollama,offline"
    assert result.data["env"]["AGENT_OLLAMA_MODEL"] == "openclaw:latest"
    assert "HF_TOKEN" not in result.data["env"]
    assert result.data["chat_url"].endswith("/api/agent/chat")


def test_generate_blocks_cloud_models_without_api_path() -> None:
    result = ollama_tool.generate("hello", model="glm-5.1:cloud")
    assert not result.ok
    assert result.message == "Cloud models are blocked by default"

    dashed = ollama_tool.generate("hello", model="mistral-large-3:675b-cloud")
    assert not dashed.ok
    assert dashed.message == "Cloud models are blocked by default"


def test_list_models_filters_cloud(monkeypatch) -> None:
    class Proc:
        returncode = 0
        stderr = ""
        stdout = "NAME ID SIZE MODIFIED\nopenclaw:latest abc 1GB now\nglm-5.1:cloud def - now\n"

    monkeypatch.setattr(ollama_tool, "_ollama_exe", lambda: "ollama")
    monkeypatch.setattr(ollama_tool.subprocess, "run", lambda *args, **kwargs: Proc())

    result = ollama_tool.list_models()
    assert result.ok
    assert [row["name"] for row in result.data["models"]] == ["openclaw:latest"]


def test_list_models_filters_dash_cloud(monkeypatch) -> None:
    class Proc:
        returncode = 0
        stderr = ""
        stdout = "NAME ID SIZE MODIFIED\nmistral-large-3:675b-cloud abc - now\nopenclaw:latest def 1GB now\n"

    monkeypatch.setattr(ollama_tool, "_ollama_exe", lambda: "ollama")
    monkeypatch.setattr(ollama_tool.subprocess, "run", lambda *args, **kwargs: Proc())

    result = ollama_tool.list_models()
    assert result.ok
    assert [row["name"] for row in result.data["models"]] == ["openclaw:latest"]


def test_health_reports_unreachable(monkeypatch) -> None:
    monkeypatch.setattr(ollama_tool, "_request_json", lambda *args, **kwargs: (None, "connection refused"))
    result = ollama_tool.health()
    assert not result.ok
    assert result.data["error"] == "connection refused"


def test_smoke_accepts_prompt_and_generation_options(monkeypatch) -> None:
    captured = {}

    def _fake_generate(prompt: str, **kwargs):
        captured["prompt"] = prompt
        captured.update(kwargs)
        return ollama_tool.ToolResult(True, "generate", "ok", {"text": "OLLAMA_OK"})

    monkeypatch.setattr(ollama_tool, "generate", _fake_generate)

    result = ollama_tool.smoke(
        prompt="Say OLLAMA_OK and one short readiness sentence.",
        model="qwen2.5-coder:1.5b",
        url="http://127.0.0.1:11434",
        timeout_s=90,
        num_predict=64,
        temperature=0.1,
    )

    assert result.ok
    assert captured == {
        "prompt": "Say OLLAMA_OK and one short readiness sentence.",
        "model": "qwen2.5-coder:1.5b",
        "url": "http://127.0.0.1:11434",
        "timeout_s": 90,
        "num_predict": 64,
        "temperature": 0.1,
    }

from scripts.system.kimi_code_connector import inspect_connector, run_cli_smoke


def test_kimi_code_connector_reports_bus_contract() -> None:
    report = inspect_connector()

    assert report["schema_version"] == "scbe_kimi_code_connector_v1"
    assert report["provider_refs"]["kimi_code"] == "kimi:kimi-for-coding"
    assert report["provider_refs"]["moonshot_platform"] == "moonshot:kimi-k2.6"
    assert report["agent_bus_contract"]["lane_signal"] == "provider-pair:ollama->kimi:agentic-coding"
    assert "kimi" in report["key_mirror"]
    assert "moonshot" in report["key_mirror"]
    assert "cli_smoke_command" in report["agent_bus_contract"]
    assert "acp_command" in report["agent_bus_contract"]


def test_kimi_code_cli_smoke_reports_missing_cli(monkeypatch) -> None:
    monkeypatch.setattr("scripts.system.kimi_code_connector.shutil.which", lambda _: None)

    report = run_cli_smoke()

    assert report["ok"] is False
    assert report["status"] == "missing_cli"

import json

import scripts.system.openclaw_browser_bridge as bridge
from scripts.system.openclaw_browser_bridge import (
    ensure_browser_running,
    load_openclaw_config,
    resolve_auth_headers,
    resolve_browser_base_url,
    start_browser,
    stop_browser,
)


def test_resolve_browser_base_url_falls_back_to_gateway_plus_two():
    cfg = {"gateway": {"port": 18789}}
    assert resolve_browser_base_url(cfg) == "http://127.0.0.1:18791"


def test_resolve_auth_headers_prefers_bearer_token():
    cfg = {"gateway": {"auth": {"token": "abc123", "password": "ignored"}}}
    assert resolve_auth_headers(cfg) == {"Authorization": "Bearer abc123"}


def test_load_openclaw_config_reads_json(tmp_path):
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(json.dumps({"gateway": {"port": 19001}}), encoding="utf-8")
    loaded = load_openclaw_config(str(config_path))
    assert loaded["gateway"]["port"] == 19001


def test_start_and_stop_browser_use_profile_payload(monkeypatch):
    calls = []

    def fake_request_json(base_url, path, **kwargs):
        calls.append((base_url, path, kwargs))
        return {"ok": True}

    monkeypatch.setattr(bridge, "request_json", fake_request_json)

    start_browser("http://127.0.0.1:18791", headers={"Authorization": "Bearer x"}, profile="openclaw", timeout=5)
    stop_browser("http://127.0.0.1:18791", headers={"Authorization": "Bearer x"}, profile="openclaw", timeout=5)

    assert calls[0][1] == "/start"
    assert calls[0][2]["body"] == {"profile": "openclaw"}
    assert calls[1][1] == "/stop"
    assert calls[1][2]["body"] == {"profile": "openclaw"}


def test_ensure_browser_running_starts_when_status_is_not_running(monkeypatch):
    calls = []
    responses = iter([{"running": False}, {"ok": True}, {"running": True}])

    def fake_request_json(base_url, path, **kwargs):
        calls.append(path)
        return next(responses)

    monkeypatch.setattr(bridge, "request_json", fake_request_json)

    payload = ensure_browser_running("http://127.0.0.1:18791", headers={}, profile="openclaw", timeout=5)

    assert payload["running"] is True
    assert calls == ["/", "/start", "/"]


def test_ensure_browser_running_skips_start_when_already_running(monkeypatch):
    calls = []

    def fake_request_json(base_url, path, **kwargs):
        calls.append(path)
        return {"running": True}

    monkeypatch.setattr(bridge, "request_json", fake_request_json)

    payload = ensure_browser_running("http://127.0.0.1:18791", headers={}, profile="openclaw", timeout=5)

    assert payload["running"] is True
    assert calls == ["/"]

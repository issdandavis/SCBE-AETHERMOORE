from scripts.benchmark.harness_live_smoke import _content_is_jsonish, build_chat_payload


def test_moonshot_kimi_k26_smoke_uses_required_temperature() -> None:
    payload = build_chat_payload("moonshot", "kimi-k2.6")

    assert payload["temperature"] == 1


def test_other_smoke_payloads_stay_deterministic() -> None:
    payload = build_chat_payload("kimi", "kimi-for-coding")

    assert payload["temperature"] == 0


def test_smoke_accepts_embedded_json_after_reasoning_text() -> None:
    content = 'thinking first\n{"ok":true,"role":"harness-smoke","tokens_saved":true}\n'

    assert _content_is_jsonish(content) is True

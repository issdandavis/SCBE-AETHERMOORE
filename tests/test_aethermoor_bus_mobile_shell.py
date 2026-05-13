from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "kindle-app" / "www"


def _has_https_host(text: str, host: str) -> bool:
    return any(
        urlparse(match.group(0)).hostname == host
        for match in re.finditer(r"https://[^\s\"'<>]+", text)
    )


def test_mobile_entrypoint_is_aethermoor_bus_not_legacy_browser_redirect() -> None:
    body = (WWW / "index.html").read_text(encoding="utf-8")
    assert "Aethermoor Bus" in body
    assert "aetherbrowser.html" not in body
    assert '<meta http-equiv="refresh"' not in body


def test_mobile_chat_is_backend_proxy_not_token_first_hf_form() -> None:
    body = (WWW / "chat.html").read_text(encoding="utf-8")
    assert "/api/agent/chat" in body
    assert "/api/agent/search" in body
    assert "/api/agent/storage" in body
    forbidden = [
        "HF token",
        "Hugging Face token",
        "pollyToken",
        "router.huggingface.co",
        "static/polly-hf-chat.js",
    ]
    for phrase in forbidden:
        assert phrase not in body


def test_native_phone_shell_defaults_to_public_backend_not_emulator_loopback() -> None:
    body = (WWW / "static" / "phone-shell.js").read_text(encoding="utf-8")
    assert "if (isKindleApp)" in body
    assert _has_https_host(body, "scbe-agent-bridge-vercel.vercel.app")
    assert "aethermoor.agentApiBase" in body


def test_manifest_uses_aethermoor_bus_branding() -> None:
    body = (WWW / "manifest.json").read_text(encoding="utf-8")
    assert '"name": "Aethermoor Bus"' in body
    assert '"short_name": "AetherBus"' in body

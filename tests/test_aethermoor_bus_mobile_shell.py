from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PWA = ROOT / "apps" / "mobile" / "pwa"


def _read(relative_path: str) -> str:
    path = PWA / relative_path
    assert path.exists(), f"missing mobile PWA source: {path}"
    return path.read_text(encoding="utf-8")


def test_mobile_entrypoint_is_the_aethermoor_bus_pwa() -> None:
    index = _read("index.html")
    app = _read("src/App.tsx")
    assert "Aethermoor Bus" in index
    assert "Aethermoor Bus" in app
    assert 'id="root"' in index
    assert 'src="/src/main.tsx"' in index
    assert '<meta http-equiv="refresh"' not in index


def test_mobile_uses_the_governed_v1_agent_bus_routes() -> None:
    sources = "\n".join(
        _read(path)
        for path in [
            "src/components/AgentList.tsx",
            "src/components/BusFeed.tsx",
            "src/components/TriggerPanel.tsx",
        ]
    )
    assert "/v1/agents" in sources
    assert "/v1/bus/events?limit=50" in sources
    assert "/v1/agents/dispatch" in sources
    assert "router.huggingface.co" not in sources


def test_mobile_backend_is_operator_configured_without_loopback_defaults() -> None:
    auth = _read("src/state/auth.ts")
    assert "aethermoor.backend_url" in auth
    assert "Authorization" in auth
    assert "Bearer ${token}" in auth
    for loopback in ["localhost", "127.0.0.1", "10.0.2.2"]:
        assert loopback not in auth


def test_manifest_uses_aethermoor_bus_branding() -> None:
    config = _read("vite.config.ts")
    twa = (ROOT / "apps" / "mobile" / "twa" / "twa-manifest.json").read_text(
        encoding="utf-8"
    )
    assert "VitePWA" in config
    assert "name: 'Aethermoor Bus'" in config
    assert '"name": "Aethermoor Bus"' in twa
    assert '"packageId": "io.aethermoor.bus"' in twa

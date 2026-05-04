from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_SERVER = ROOT / "scripts" / "aetherbrowser" / "api_server.py"


def test_aetherbrowser_api_server_does_not_allow_wildcard_cors_with_credentials() -> None:
    source = API_SERVER.read_text(encoding="utf-8")

    assert "allow_origins=[\"*\"]" not in source
    assert "allow_credentials=True" not in source
    assert "SCBE_CORS_ORIGINS" in source
    assert "SCBE_ALLOW_WILDCARD_CORS" in source
    assert "allow_credentials=False" in source

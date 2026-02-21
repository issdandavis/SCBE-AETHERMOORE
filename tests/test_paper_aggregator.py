from src.paper_bundle_normalizer import normalize_bundle
from src.symphonic_cipher.scbe_aethermoore.layers.paper_aggregator import (
    aggregate_sources,
)


def test_aggregate_sources_allow_path():
    def allow_gate(intent, d):
        assert "repos" in intent
        return {
            "status": "ALLOW",
            "decision": "ALLOW",
            "d_star": 0.12,
            "risk_prime": 0.21,
            "H": 1.03,
        }

    def fake_json_fetch(url):
        return {"source_url": url}

    result = aggregate_sources(
        repos=["issdandavis/SCBE-AETHERMOORE"],
        npm_package="izdandavis",
        space_files=["roadmap.md"],
        github_fetcher=fake_json_fetch,
        npm_fetcher=fake_json_fetch,
        gate_fn=allow_gate,
    )

    assert result["status"] == "ALLOW"
    assert result["gate"]["decision"] == "ALLOW"
    assert len(result["bundle_hash"]) == 64
    assert result["bundle"]["fetch_errors"] == []
    assert "issdandavis/SCBE-AETHERMOORE" in result["bundle"]["repos"]


def test_aggregate_sources_quarantine_short_circuit():
    calls = {"count": 0}

    def quarantine_gate(intent, d):
        return {"status": "QUARANTINE", "decision": "DENY"}

    def fake_json_fetch(url):
        calls["count"] += 1
        return {"url": url}

    result = aggregate_sources(
        repos=["issdandavis/SCBE-AETHERMOORE"],
        npm_package="izdandavis",
        github_fetcher=fake_json_fetch,
        npm_fetcher=fake_json_fetch,
        gate_fn=quarantine_gate,
    )

    assert result["status"] == "QUARANTINE"
    assert result["bundle"] == {}
    assert calls["count"] == 0


def test_normalize_bundle_returns_per_section_results():
    bundle = {
        "repos": {"issdandavis/SCBE-AETHERMOORE": [{"name": "README.md"}]},
        "npm": {"name": "izdandavis", "version": "1.0.0"},
        "space": [{"file": "roadmap.md", "content": "example"}],
    }

    result = normalize_bundle(bundle, norm_threshold=0.95)

    assert result["status"] in {"ALLOW", "QUARANTINE"}
    assert set(result["sections"].keys()) == set(bundle.keys())
    assert len(result["bundle_hash"]) == 64

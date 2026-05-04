from scripts.system import alphagenome_probe


def test_resolve_key_accepts_primary_env_name():
    key_name, value = alphagenome_probe.resolve_key({"ALPHAGENOME_API_KEY": "abc123"})

    assert key_name == "ALPHAGENOME_API_KEY"
    assert value == "abc123"


def test_receipt_blocks_live_without_terms(monkeypatch):
    monkeypatch.setattr(alphagenome_probe, "package_installed", lambda: True)
    monkeypatch.setattr(alphagenome_probe, "import_client_modules", lambda: (True, ""))
    monkeypatch.setenv("ALPHAGENOME_API_KEY", "secret-value")

    receipt = alphagenome_probe.build_receipt(live=True, ack_terms=False)

    assert receipt["live_allowed"] is False
    assert receipt["live_status"] == "blocked_terms_ack_required"
    assert receipt["key_fingerprint"] is not None
    assert "secret-value" not in str(receipt)


def test_receipt_allows_local_ready_without_live(monkeypatch):
    monkeypatch.setattr(alphagenome_probe, "package_installed", lambda: True)
    monkeypatch.setattr(alphagenome_probe, "import_client_modules", lambda: (True, ""))
    monkeypatch.delenv("ALPHAGENOME_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_GENOME_API_KEY", raising=False)

    receipt = alphagenome_probe.build_receipt(live=False, ack_terms=False)

    assert receipt["route_decision"] == "ALLOW_LOCAL_CLIENT_READY"
    assert receipt["live_status"] == "not_requested"
    assert receipt["key_present"] is False


def test_receipt_ready_for_future_live_fixture_when_gates_present(monkeypatch):
    monkeypatch.setattr(alphagenome_probe, "package_installed", lambda: True)
    monkeypatch.setattr(alphagenome_probe, "import_client_modules", lambda: (True, ""))
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "another-secret")

    receipt = alphagenome_probe.build_receipt(live=True, ack_terms=True)

    assert receipt["live_allowed"] is True
    assert receipt["live_status"] == "ready_for_future_live_fixture"
    assert receipt["route_decision"] == "ALLOW_WITH_TERMS_AND_QUOTA_GATE"
    assert receipt["connector_contract"]["training_data_policy"].startswith("do_not_store")


def test_receipt_reports_missing_package(monkeypatch):
    monkeypatch.setattr(alphagenome_probe, "package_installed", lambda: False)

    receipt = alphagenome_probe.build_receipt(live=False, ack_terms=False)

    assert receipt["package_installed"] is False
    assert receipt["import_ok"] is False
    assert receipt["blocked_reason"] == "pip_install_or_local_clone_required"

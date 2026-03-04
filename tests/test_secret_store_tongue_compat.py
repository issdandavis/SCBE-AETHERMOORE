from pathlib import Path

from src.security import secret_store


def test_set_secret_default_tongue_lowercase(tmp_path: Path, monkeypatch):
    store_file = tmp_path / "secret-store.json"
    monkeypatch.setenv("SCBE_SECRET_STORE_PATH", str(store_file))

    secret_store.set_secret("TEST_KEY", "hello-world")
    payload = secret_store._load_store()  # noqa: SLF001 - test-only introspection
    assert payload["secrets"]["TEST_KEY"]["tongue"] == "ko"
    assert secret_store.get_secret("TEST_KEY", "") == "hello-world"


def test_get_secret_reads_uppercase_legacy_tongue(tmp_path: Path, monkeypatch):
    store_file = tmp_path / "secret-store.json"
    monkeypatch.setenv("SCBE_SECRET_STORE_PATH", str(store_file))

    secret_store.set_secret("LEGACY_KEY", "legacy-value")
    payload = secret_store._load_store()  # noqa: SLF001 - test-only introspection
    payload["secrets"]["LEGACY_KEY"]["tongue"] = "KO"
    secret_store._write_store(payload)  # noqa: SLF001 - test-only introspection

    assert secret_store.get_secret("LEGACY_KEY", "") == "legacy-value"

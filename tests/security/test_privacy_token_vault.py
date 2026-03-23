from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI required")


def test_alias_generation_is_deterministic_and_typed(tmp_path) -> None:
    from src.security.privacy_token_vault import (
        PrivacyTokenVault,
        VAULT_KIND_EMAIL,
        VAULT_KIND_PERSON,
    )

    vault = PrivacyTokenVault(tmp_path, master_secret="unit-test-master-key", vault_name="unit")

    alias_1 = vault.alias_for("User.Name+tag@example.com", VAULT_KIND_EMAIL)
    alias_2 = vault.alias_for(" user.name+tag@EXAMPLE.com ", VAULT_KIND_EMAIL)
    alias_3 = vault.alias_for("User.Name+tag@example.com", VAULT_KIND_PERSON)

    assert alias_1 == alias_2
    assert alias_1.startswith("email_")
    assert alias_3.startswith("person_")
    assert alias_1 != alias_3


def test_roundtrip_lookup_and_public_metadata(tmp_path) -> None:
    from src.security.privacy_token_vault import (
        PrivacyTokenVault,
        VAULT_KIND_EMAIL,
        VAULT_KIND_GENERIC,
    )

    vault = PrivacyTokenVault(tmp_path, master_secret="unit-test-master-key", vault_name="unit")

    entry = vault.put(
        "Sensitive.User@example.com",
        kind=VAULT_KIND_EMAIL,
        metadata={"source": "inbox", "category": "contact"},
    )

    assert vault.has(entry.alias) is True
    assert vault.get(entry.alias) == "Sensitive.User@example.com"
    assert vault.lookup(" sensitive.user@EXAMPLE.com ", kind=VAULT_KIND_EMAIL) == "Sensitive.User@example.com"

    public = vault.export_public_index()
    assert entry.alias in public["entries"]
    assert public["entries"][entry.alias]["kind"] == VAULT_KIND_EMAIL
    assert "Sensitive.User@example.com" not in json.dumps(public)

    generic_entry = vault.put("Account-90210", kind=VAULT_KIND_GENERIC)
    assert vault.get(generic_entry.alias) == "Account-90210"


def test_encrypted_storage_does_not_write_plaintext_value(tmp_path) -> None:
    from src.security.privacy_token_vault import PrivacyTokenVault, VAULT_KIND_ACCOUNT

    vault = PrivacyTokenVault(tmp_path, master_secret="unit-test-master-key", vault_name="unit")
    secret_value = "acct-very-private-123456"
    entry = vault.put(secret_value, kind=VAULT_KIND_ACCOUNT, metadata={"owner": "billing"})

    index_text = (tmp_path / "index.json").read_text(encoding="utf-8")
    blob_path = Path(entry.blob_file)
    blob_bytes = blob_path.read_bytes()

    assert secret_value not in index_text
    assert secret_value.encode("utf-8") not in blob_bytes
    assert vault.describe(entry.alias)["value_sha256"] == entry.value_sha256


def test_protect_returns_placeholder_and_preserves_lookup_metadata(tmp_path) -> None:
    from src.security.privacy_token_vault import (
        PrivacyTokenVault,
        VAULT_KIND_EMAIL,
        decode_placeholder_alias,
    )

    vault = PrivacyTokenVault(tmp_path, master_secret="unit-test-master-key", vault_name="unit")
    token = vault.protect(
        "Sensitive.User@example.com",
        kind=VAULT_KIND_EMAIL,
        source_file="notes/round-table/ROUND_TABLE.md",
    )

    assert token.startswith("<<EMAIL:")
    alias = decode_placeholder_alias(token)
    assert vault.get(alias) == "Sensitive.User@example.com"
    payload = vault.get(alias, include_metadata=True)
    assert payload["metadata"]["source_file"] == "notes/round-table/ROUND_TABLE.md"

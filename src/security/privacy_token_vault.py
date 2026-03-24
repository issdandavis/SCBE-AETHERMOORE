"""Windows-first reversible token vault for privacy-preserving pseudonymization."""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from ctypes import wintypes

from .secret_store import sanitize_for_report


VAULT_KIND_EMAIL = "email"
VAULT_KIND_PHONE = "phone"
VAULT_KIND_PERSON = "person"
VAULT_KIND_ORG = "org"
VAULT_KIND_ACCOUNT = "account"
VAULT_KIND_URL = "url"
VAULT_KIND_GENERIC = "generic"

VAULT_KINDS = {
    VAULT_KIND_EMAIL,
    VAULT_KIND_PHONE,
    VAULT_KIND_PERSON,
    VAULT_KIND_ORG,
    VAULT_KIND_ACCOUNT,
    VAULT_KIND_URL,
    VAULT_KIND_GENERIC,
}

MASTER_SECRET_ENV_KEYS = (
    "SCBE_PRIVACY_VAULT_MASTER_KEY",
    "SCBE_PRIVACY_TOKEN_MASTER_KEY",
    "SCBE_PRIVACY_TOKEN_KEY",
)

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("PrivacyTokenVault requires Windows DPAPI and is not supported on this platform.")


def _blob_from_bytes(payload: bytes) -> DATA_BLOB:
    if not payload:
        payload = b"\x00"
    buf = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
    return DATA_BLOB(len(payload), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _dpapi_protect(payload: bytes, entropy: bytes, description: str) -> bytes:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    in_blob = _blob_from_bytes(payload)
    ent_blob = _blob_from_bytes(entropy)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        description,
        ctypes.byref(ent_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _bytes_from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(payload: bytes, entropy: bytes) -> bytes:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    in_blob = _blob_from_bytes(payload)
    ent_blob = _blob_from_bytes(entropy)
    out_blob = DATA_BLOB()
    desc = wintypes.LPWSTR()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        ctypes.byref(desc),
        ctypes.byref(ent_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _bytes_from_blob(out_blob)
    finally:
        if desc:
            kernel32.LocalFree(desc)
        kernel32.LocalFree(out_blob.pbData)


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_identifier(value: str, kind: str = VAULT_KIND_GENERIC) -> str:
    kind = (kind or VAULT_KIND_GENERIC).strip().lower()
    raw = str(value or "")
    if kind == VAULT_KIND_EMAIL:
        return _collapse_whitespace(raw).lower()
    if kind == VAULT_KIND_PHONE:
        cleaned = re.sub(r"[^0-9+]", "", raw.strip())
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]
        if cleaned.count("+") > 1:
            cleaned = cleaned.replace("+", "")
        if cleaned and not cleaned.startswith("+") and raw.strip().startswith("+"):
            cleaned = "+" + cleaned.lstrip("+")
        return cleaned
    if kind == VAULT_KIND_URL:
        parts = urlsplit(raw.strip())
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        path = re.sub(r"/{2,}", "/", parts.path or "")
        if path.endswith("/") and path != "/":
            path = path.rstrip("/")
        return urlunsplit((scheme, netloc, path, parts.query, ""))
    return _collapse_whitespace(raw).lower()


def _kind_prefix(kind: str) -> str:
    kind = (kind or VAULT_KIND_GENERIC).strip().lower()
    if kind not in VAULT_KINDS:
        kind = VAULT_KIND_GENERIC
    return kind


def _placeholder_token(alias: str, kind: str) -> str:
    return f"<<{_kind_prefix(kind).upper()}:{'~'.join(alias)}>>"


def decode_placeholder_alias(token: str) -> str:
    prefix, separator, remainder = token.partition(":")
    if not prefix.startswith("<<") or not separator or not remainder.endswith(">>"):
        raise ValueError(f"invalid placeholder token: {token!r}")
    return remainder[:-2].replace("~", "")


@dataclass(frozen=True)
class VaultEntry:
    alias: str
    kind: str
    blob_file: str
    value_sha256: str
    value_length: int
    created_at_utc: str
    updated_at_utc: str
    metadata: dict[str, Any]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "kind": self.kind,
            "blob_file": self.blob_file,
            "value_sha256": self.value_sha256,
            "value_length": self.value_length,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "metadata": sanitize_for_report(self.metadata),
        }


class PrivacyTokenVault:
    """Reversible pseudonymization vault with Windows DPAPI-backed storage."""

    def __init__(
        self,
        vault_root: str | Path | None = None,
        *,
        master_secret: str | bytes | None = None,
        vault_name: str = "privacy-token-vault",
    ) -> None:
        _require_windows()
        self.vault_root = Path(vault_root) if vault_root is not None else Path.home() / ".scbe" / "privacy_token_vault"
        self.vault_name = _collapse_whitespace(vault_name or "privacy-token-vault").lower().replace(" ", "-")
        self.index_path = self.vault_root / "index.json"
        self.master_secret_path = self.vault_root / "master_secret.bin"
        self.blob_dir = self.vault_root / "blobs"
        self.vault_root.mkdir(parents=True, exist_ok=True)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self._master_secret = self._load_or_create_master_secret(master_secret)
        self._index = self._load_index()

    @property
    def master_secret(self) -> bytes:
        return self._master_secret

    def _master_secret_entropy(self) -> bytes:
        return f"SCBE|PrivacyTokenVault|master|{self.vault_name}".encode("utf-8")

    def _blob_entropy(self, alias: str, kind: str) -> bytes:
        return b"|".join(
            [
                b"SCBE",
                b"PrivacyTokenVault",
                b"blob",
                self.vault_name.encode("utf-8"),
                kind.encode("utf-8"),
                alias.encode("utf-8"),
                self._master_secret[:16],
            ]
        )

    def _load_or_create_master_secret(self, override: str | bytes | None) -> bytes:
        if override is not None:
            if isinstance(override, bytes):
                secret = bytes(override)
            else:
                secret = str(override).encode("utf-8")
            if not secret:
                raise ValueError("master_secret cannot be empty")
            return secret

        for env_name in MASTER_SECRET_ENV_KEYS:
            env_value = os.getenv(env_name, "").strip()
            if env_value:
                return env_value.encode("utf-8")

        if self.master_secret_path.exists():
            encrypted = self.master_secret_path.read_bytes()
            return _dpapi_unprotect(encrypted, self._master_secret_entropy())

        secret = secrets.token_bytes(32)
        encrypted = _dpapi_protect(
            secret,
            self._master_secret_entropy(),
            f"SCBE Privacy Token Vault {self.vault_name} master secret",
        )
        self.master_secret_path.write_bytes(encrypted)
        return secret

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {
                "version": 1,
                "vault_name": self.vault_name,
                "created_at_utc": _utc_now(),
                "updated_at_utc": _utc_now(),
                "entries": {},
            }
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("index payload must be a JSON object")
            payload.setdefault("entries", {})
            payload.setdefault("version", 1)
            payload.setdefault("vault_name", self.vault_name)
            payload.setdefault("created_at_utc", _utc_now())
            payload["updated_at_utc"] = _utc_now()
            return payload
        except Exception:
            return {
                "version": 1,
                "vault_name": self.vault_name,
                "created_at_utc": _utc_now(),
                "updated_at_utc": _utc_now(),
                "entries": {},
            }

    def _save_index(self) -> None:
        self._index["updated_at_utc"] = _utc_now()
        self.index_path.write_text(json.dumps(self._index, indent=2, ensure_ascii=True), encoding="utf-8")

    def alias_for(self, value: str, kind: str = VAULT_KIND_GENERIC) -> str:
        kind = _kind_prefix(kind)
        normalized = normalize_identifier(value, kind)
        message = f"{kind}|{normalized}".encode("utf-8")
        digest = hmac.new(self._master_secret, message, hashlib.sha256).hexdigest()
        return f"{kind}_{digest[:24]}"

    def _entry_blob_path(self, alias: str, kind: str) -> Path:
        return self.blob_dir / kind / f"{alias}.bin"

    def _encrypt_record(self, alias: str, kind: str, payload: dict[str, Any]) -> bytes:
        packed = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        entropy = self._blob_entropy(alias, kind)
        return _dpapi_protect(packed, entropy, f"SCBE Privacy Token Vault {self.vault_name} entry {alias}")

    def _decrypt_record(self, alias: str, kind: str, blob: bytes) -> dict[str, Any]:
        entropy = self._blob_entropy(alias, kind)
        raw = _dpapi_unprotect(blob, entropy)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("decrypted payload must be a JSON object")
        return payload

    def put(self, value: str, *, kind: str = VAULT_KIND_GENERIC, metadata: dict[str, Any] | None = None) -> VaultEntry:
        kind = _kind_prefix(kind)
        normalized = normalize_identifier(value, kind)
        alias = self.alias_for(value, kind)
        value_sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        safe_metadata = sanitize_for_report(metadata or {})
        now = _utc_now()
        blob_path = self._entry_blob_path(alias, kind)
        blob_path.parent.mkdir(parents=True, exist_ok=True)

        entry = self._index.get("entries", {}).get(alias)
        if entry and entry.get("value_sha256") not in {None, value_sha256}:
            raise ValueError(f"alias collision for {alias}")

        record_payload = {
            "alias": alias,
            "kind": kind,
            "value": value,
            "normalized": normalized,
            "metadata": safe_metadata,
            "created_at_utc": entry.get("created_at_utc") if isinstance(entry, dict) else now,
        }
        encrypted = self._encrypt_record(alias, kind, record_payload)
        blob_path.write_bytes(encrypted)

        stored_entry = VaultEntry(
            alias=alias,
            kind=kind,
            blob_file=str(blob_path),
            value_sha256=value_sha256,
            value_length=len(value),
            created_at_utc=str(entry.get("created_at_utc", now)) if isinstance(entry, dict) else now,
            updated_at_utc=now,
            metadata=safe_metadata,
        )
        self._index.setdefault("entries", {})[alias] = stored_entry.to_public_dict()
        self._save_index()
        return stored_entry

    def protect(
        self,
        value: str,
        *,
        kind: str = VAULT_KIND_GENERIC,
        source_file: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        safe_metadata = dict(metadata or {})
        if source_file:
            safe_metadata.setdefault("source_file", source_file)
        entry = self.put(value, kind=kind, metadata=safe_metadata or None)
        return _placeholder_token(entry.alias, kind)

    def tokenize(
        self,
        value: str,
        *,
        kind: str = VAULT_KIND_GENERIC,
        source_file: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.protect(value, kind=kind, source_file=source_file, metadata=metadata)

    def get(self, alias: str, *, include_metadata: bool = False) -> str | dict[str, Any]:
        entry = self._index.get("entries", {}).get(alias)
        if not isinstance(entry, dict):
            raise KeyError(alias)
        blob_path = Path(entry["blob_file"])
        if not blob_path.exists():
            raise FileNotFoundError(blob_path)
        payload = self._decrypt_record(alias, str(entry.get("kind", VAULT_KIND_GENERIC)), blob_path.read_bytes())
        if include_metadata:
            return payload
        return str(payload.get("value", ""))

    def lookup(
        self,
        value: str,
        *,
        kind: str = VAULT_KIND_GENERIC,
        include_metadata: bool = False,
    ) -> str | dict[str, Any]:
        alias = self.alias_for(value, kind)
        return self.get(alias, include_metadata=include_metadata)

    def has(self, alias: str) -> bool:
        return alias in self._index.get("entries", {})

    def describe(self, alias: str) -> dict[str, Any]:
        entry = self._index.get("entries", {}).get(alias)
        if not isinstance(entry, dict):
            raise KeyError(alias)
        return dict(entry)

    def export_public_index(self) -> dict[str, Any]:
        entries: dict[str, Any] = {}
        for alias, entry in self._index.get("entries", {}).items():
            if isinstance(entry, dict):
                entries[alias] = sanitize_for_report(entry)
        return {
            "version": self._index.get("version", 1),
            "vault_name": self._index.get("vault_name", self.vault_name),
            "created_at_utc": self._index.get("created_at_utc"),
            "updated_at_utc": self._index.get("updated_at_utc"),
            "entries": entries,
        }

    def export_public_index_json(self) -> str:
        return json.dumps(self.export_public_index(), indent=2, ensure_ascii=True)

    def refresh_index(self) -> None:
        self._index = self._load_index()

    def count(self) -> int:
        entries = self._index.get("entries", {})
        return len(entries) if isinstance(entries, dict) else 0


def create_vault(vault_dir: str | Path | None = None, **kwargs: Any) -> PrivacyTokenVault:
    return PrivacyTokenVault(vault_root=vault_dir, **kwargs)


def get_vault(vault_dir: str | Path | None = None, **kwargs: Any) -> PrivacyTokenVault:
    return create_vault(vault_dir=vault_dir, **kwargs)


def build_vault(vault_dir: str | Path | None = None, **kwargs: Any) -> PrivacyTokenVault:
    return create_vault(vault_dir=vault_dir, **kwargs)


__all__ = [
    "PrivacyTokenVault",
    "VaultEntry",
    "VAULT_KIND_ACCOUNT",
    "VAULT_KIND_EMAIL",
    "VAULT_KIND_GENERIC",
    "VAULT_KIND_ORG",
    "VAULT_KIND_PERSON",
    "VAULT_KIND_PHONE",
    "VAULT_KIND_URL",
    "build_vault",
    "create_vault",
    "decode_placeholder_alias",
    "get_vault",
    "normalize_identifier",
]

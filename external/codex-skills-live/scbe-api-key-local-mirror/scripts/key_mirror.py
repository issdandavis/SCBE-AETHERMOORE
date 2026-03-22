#!/usr/bin/env python3
"""Secure local tokenized mirror for API keys (Windows DPAPI).

This script keeps a second local destination for secrets without storing plaintext.
"""

from __future__ import annotations

import argparse
import ctypes
import getpass
import hashlib
import json
import os
import secrets
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _blob_from_bytes(payload: bytes) -> DATA_BLOB:
    if not payload:
        payload = b"\x00"
    c_buf = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
    return DATA_BLOB(len(payload), ctypes.cast(c_buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def dpapi_protect(payload: bytes, entropy: bytes, description: str) -> bytes:
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


def dpapi_unprotect(payload: bytes, entropy: bytes) -> bytes:
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


def slug(text: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe or "key"


@dataclass
class Item:
    token_id: str
    created_at: str
    blob: str
    sha256: str
    source: str


class KeyMirror:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tokens_dir = self.root / "tokens"
        self.index_file = self.root / "index.json"

    def ensure(self) -> None:
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self._save({"version": 1, "updated_at": utc_now(), "records": {}})

    def _load(self) -> dict[str, Any]:
        self.ensure()
        return json.loads(self.index_file.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = utc_now()
        self.index_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def store(self, service: str, key_value: str, source: str) -> dict[str, Any]:
        payload = self._load()
        records = payload.setdefault("records", {})

        token_id = f"tok_{slug(service)}_{secrets.token_hex(6)}"
        blob_path = self.tokens_dir / f"{token_id}.bin"
        entropy = f"SCBE|{service}|v1".encode("utf-8")
        encrypted = dpapi_protect(key_value.encode("utf-8"), entropy, f"SCBE Key Mirror {service}")
        blob_path.write_bytes(encrypted)

        digest = hashlib.sha256(key_value.encode("utf-8")).hexdigest()
        item = Item(
            token_id=token_id,
            created_at=utc_now(),
            blob=str(blob_path),
            sha256=digest,
            source=source,
        )

        service_slot = records.setdefault(service, {"latest": token_id, "items": []})
        service_slot["latest"] = token_id
        service_slot["items"].append(item.__dict__)
        self._save(payload)

        return {
            "service": service,
            "token_id": token_id,
            "stored_blob": str(blob_path),
            "fingerprint": digest[:12],
        }

    def list_services(self) -> list[dict[str, Any]]:
        payload = self._load()
        records = payload.get("records", {})
        result: list[dict[str, Any]] = []
        for service, slot in sorted(records.items()):
            items = slot.get("items", [])
            latest = slot.get("latest", "")
            last = items[-1] if items else {}
            result.append(
                {
                    "service": service,
                    "versions": len(items),
                    "latest": latest,
                    "updated_at": last.get("created_at", ""),
                    "fingerprint": (last.get("sha256", "")[:12] if last.get("sha256") else ""),
                }
            )
        return result

    def _find_latest_item(self, service: str) -> dict[str, Any]:
        payload = self._load()
        slot = payload.get("records", {}).get(service)
        if not slot or not slot.get("items"):
            raise KeyError(f"No key stored for service '{service}'")
        latest = slot.get("latest")
        for item in reversed(slot["items"]):
            if item.get("token_id") == latest:
                return item
        return slot["items"][-1]

    def resolve(self, service: str) -> dict[str, Any]:
        item = self._find_latest_item(service)
        blob_path = Path(item["blob"])
        encrypted = blob_path.read_bytes()
        entropy = f"SCBE|{service}|v1".encode("utf-8")
        raw = dpapi_unprotect(encrypted, entropy).decode("utf-8")
        return {
            "service": service,
            "token_id": item["token_id"],
            "fingerprint": item["sha256"][:12],
            "value": raw,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Secure tokenized local mirror for API keys (DPAPI).")
    parser.add_argument("command", choices=["store", "list", "resolve", "doctor"])
    parser.add_argument("--service", default="", help="Service name (e.g. world_anvil).")
    parser.add_argument("--env", default="", help="Read key value from environment variable.")
    parser.add_argument("--key", default="", help="Key value (avoid if possible; use --env or prompt).")
    parser.add_argument("--env-out", default="", help="Output env var name for resolve.")
    parser.add_argument("--raw", action="store_true", help="Print raw resolved key.")
    parser.add_argument(
        "--vault-dir",
        default=str(Path.home() / ".scbe_keys"),
        help="Local secure vault directory.",
    )
    return parser.parse_args()


def main() -> int:
    if os.name != "nt":
        print(json.dumps({"ok": False, "error": "Windows DPAPI required"}, indent=2))
        return 1

    args = parse_args()
    mirror = KeyMirror(Path(args.vault_dir))

    if args.command == "doctor":
        mirror.ensure()
        print(json.dumps({"ok": True, "vault_dir": str(mirror.root), "index": str(mirror.index_file)}, indent=2))
        return 0

    if args.command == "list":
        print(json.dumps({"ok": True, "services": mirror.list_services()}, indent=2))
        return 0

    if args.command == "store":
        if not args.service:
            raise SystemExit("--service is required for store")

        source = "prompt"
        secret = args.key
        if args.env:
            source = f"env:{args.env}"
            secret = os.getenv(args.env, "")
        elif not secret:
            secret = getpass.getpass(f"Enter key for {args.service}: ").strip()

        if not secret:
            raise SystemExit("No key value received. Provide --env, --key, or prompt input.")

        out = mirror.store(args.service, secret, source)
        print(json.dumps({"ok": True, **out}, indent=2))
        return 0

    if args.command == "resolve":
        if not args.service:
            raise SystemExit("--service is required for resolve")
        resolved = mirror.resolve(args.service)

        if args.env_out:
            cmd = f"$env:{args.env_out}='{resolved['value']}'"
            print(json.dumps({"ok": True, "service": args.service, "token_id": resolved["token_id"], "powershell": cmd}, indent=2))
            return 0

        if args.raw:
            print(resolved["value"])
            return 0

        masked = resolved["value"][:4] + "..." + resolved["value"][-3:] if len(resolved["value"]) >= 8 else "***"
        print(
            json.dumps(
                {
                    "ok": True,
                    "service": args.service,
                    "token_id": resolved["token_id"],
                    "fingerprint": resolved["fingerprint"],
                    "masked": masked,
                },
                indent=2,
            )
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

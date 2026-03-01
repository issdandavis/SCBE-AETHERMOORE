"""Local disk-backed secret store using Sacred Tongue tokenization.

The store is intentionally lightweight and offline-first:
- secrets are kept in a JSON file on this machine
- values are encoded as Sacred Tongue tokens (not plain text)
- values can be read back through the detokenizer helpers
"""

from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER


DEFAULT_TONGUE = "KO"


def store_path() -> str:
    return os.path.expanduser(
        os.getenv(
            "SCBE_SECRET_STORE_PATH",
            os.path.join(os.path.expanduser("~"), ".scbe", "secret-store.json"),
        )
    )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_store() -> Dict[str, Any]:
    path = Path(store_path())
    if not path.exists():
        return {"version": 1, "secrets": {}}

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"version": 1, "secrets": {}}

    try:
        parsed = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {"version": 1, "secrets": {}}

    if not isinstance(parsed, dict):
        return {"version": 1, "secrets": {}}

    if "secrets" not in parsed or not isinstance(parsed["secrets"], dict):
        parsed["secrets"] = {}

    return parsed


def _write_store(payload: Dict[str, Any]) -> None:
    path = Path(store_path())
    _ensure_parent(path)
    data = {
        "version": 1,
        "secrets": payload.get("secrets", {}),
    }
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_tokens(tokens: Any) -> List[str]:
    if isinstance(tokens, str):
        # Accept space-separated or comma-separated token forms.
        if "," in tokens:
            return [t.strip() for t in tokens.split(",") if t.strip()]
        return [t.strip() for t in tokens.split() if t.strip()]
    if isinstance(tokens, list):
        return [str(t).strip() for t in tokens if str(t).strip()]
    return []


def _pick_env(name: str) -> Optional[str]:
    raw = os.getenv(name)
    if raw is not None:
        value = str(raw).strip()
        if value:
            return value
    return None


def _pick_secret_record(name: str) -> Optional[Dict[str, Any]]:
    store = _load_store()
    secrets = store.get("secrets", {})
    record = secrets.get(name)
    if isinstance(record, dict):
        return record
    return None


def get_secret(name: str, default: str = "") -> str:
    from_env = _pick_env(name)
    if from_env is not None:
        return from_env

    record = _pick_secret_record(name)
    if not record:
        return default

    encoded = _normalize_tokens(record.get("value_tokens"))
    if not encoded:
        return default

    tongue = str(record.get("tongue") or DEFAULT_TONGUE)
    try:
        raw = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, encoded)
        return raw.decode("utf-8")
    except Exception:
        return default


def set_secret(name: str, value: str, note: str = "", tongue: str = DEFAULT_TONGUE) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("secret name required")

    if not value:
        raise ValueError("secret value required")

    record = _pick_secret_record(name) or {}
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, value.encode("utf-8"))

    store = _load_store()
    store.setdefault("secrets", {})[name] = {
        "name": name,
        "tongue": tongue,
        "value_tokens": tokens,
        "note": str(note or ""),
        "created_at": record.get("created_at", _now_iso()),
        "updated_at": _now_iso(),
    }
    _write_store(store)


def remove_secret(name: str) -> bool:
    name = str(name).strip()
    if not name:
        return False

    store = _load_store()
    secrets = store.get("secrets", {})
    if name not in secrets:
        return False
    del secrets[name]
    store["secrets"] = secrets
    _write_store(store)
    return True


def list_secret_names() -> List[str]:
    store = _load_store()
    names = [str(name) for name in store.get("secrets", {}).keys()]
    return sorted(names)


def pick_secret(*names: str) -> Tuple[str, str]:
    for name in names:
        name = str(name).strip()
        if not name:
            continue
        value = get_secret(name, "")
        if value:
            return name, value
    return "", ""


def parse_api_key_mapping(raw: Any) -> Dict[str, str]:
    if isinstance(raw, dict):
        return {
            str(k): str(v)
            for k, v in raw.items()
            if str(k).strip() and str(v).strip()
        }

    if not isinstance(raw, str):
        return {}

    text = raw.strip()
    if not text:
        return {}

    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {
                    str(k): str(v)
                    for k, v in parsed.items()
                    if str(k).strip() and str(v).strip()
                }
        except json.JSONDecodeError:
            pass

    pairs: List[str] = []
    for chunk in text.replace(";", ",").replace("\n", ",").split(","):
        if chunk.strip():
            pairs.append(chunk.strip())

    result: Dict[str, str] = {}
    for pair in pairs:
        sep = ":"
        if ":" in pair:
            key, value = pair.split(":", 1)
        elif "=" in pair:
            key, value = pair.split("=", 1)
        else:
            continue
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def get_api_key_map(secret_name: str = "SCBE_VALID_API_KEYS") -> Dict[str, str]:
    raw = _pick_env(secret_name)
    if raw is not None:
        parsed = parse_api_key_mapping(raw)
        if parsed:
            return parsed

    raw = get_secret(secret_name, "")
    parsed = parse_api_key_mapping(raw)
    if parsed:
        return parsed

    legacy = parse_api_key_mapping(_pick_env("SCBE_API_KEY_MAP") or "")
    if legacy:
        return legacy

    legacy = parse_api_key_mapping(_pick_env("SCBE_API_KEYS") or "")
    return legacy


def _now_iso() -> str:
    return __import__("datetime").datetime.utcnow().isoformat() + "Z"

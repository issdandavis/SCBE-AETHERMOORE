"""Firebase helper for scbe-content-publisher skill.

This wrapper keeps secrets in local/offline secret store, then falls back to
environment variables and application-default credentials.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import os
import firebase_admin
from firebase_admin import credentials as fb_credentials
from firebase_admin import auth as fb_auth
from firebase_admin import firestore, storage as fb_storage

from src.security.secret_store import get_secret as get_secret_text


class FirebaseClient:
    _instance = None

    def __new__(
        cls,
        config_path: str = "firebase-config.json",
        project_id: Optional[str] = None,
    ):
        if cls._instance is None:
            if not firebase_admin._apps:
                _initialize_firebase_app(config_path=config_path, project_id=project_id)

            cfg_path = _resolve_config_path(config_path)
            cls._instance = super().__new__(cls)
            cls._instance._project_id = project_id or _load_env("FIREBASE_PROJECT_ID")
            cls._instance._web_config = _load_web_config(cfg_path)
            cls._instance._db = firestore.client()

        return cls._instance

    @property
    def db(self):
        """Return Firestore client."""
        return self._db

    @property
    def auth(self):
        """Return Firebase Auth module."""
        return fb_auth

    @property
    def storage(self):
        """Return Firebase Storage default bucket."""
        try:
            return fb_storage.bucket()
        except Exception:
            return None

    @property
    def web_config(self) -> Dict[str, Any]:
        """Return optional frontend Firebase web config payload."""
        return dict(self._web_config)


def _resolve_config_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    # skills/clawhub/scbe-content-publisher/utils -> repo root at parents[4]
    return Path(__file__).resolve().parents[4] / path


def _initialize_firebase_app(config_path: str = "firebase-config.json", project_id: Optional[str] = None) -> None:
    app_project = project_id or _load_env("FIREBASE_PROJECT_ID")

    # Explicit secret from local secret store (tokenized on disk).
    secret_json = get_secret_text("FIREBASE_SERVICE_ACCOUNT_KEY")
    if not secret_json:
        secret_json = get_secret_text("FIREBASE_CREDENTIALS_JSON")

    credential_path = _load_env("FIREBASE_CREDENTIALS_PATH")
    google_path = _load_env("GOOGLE_APPLICATION_CREDENTIALS")

    options = {"projectId": app_project or ""}

    if secret_json:
        parsed = _parse_json(secret_json)
        if parsed is not None:
            firebase_admin.initialize_app(fb_credentials.Certificate(parsed), options)
            return

    if credential_path and Path(credential_path).exists():
        firebase_admin.initialize_app(fb_credentials.Certificate(credential_path), options)
        return

    if google_path and Path(google_path).exists():
        firebase_admin.initialize_app(fb_credentials.Certificate(google_path), options)
        return

    firebase_admin.initialize_app(options=options)


def _parse_json(raw: str) -> Optional[dict]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _load_web_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_env(name: str) -> str:
    return str((os.environ.get(name) or "")).strip()


__all__ = ["FirebaseClient"]

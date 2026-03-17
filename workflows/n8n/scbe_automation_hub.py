from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse


def parse_allowed_hosts(raw: str) -> set[str]:
    values = {item.strip().lower() for item in str(raw or "").split(",") if item.strip()}
    values.discard("*")
    return values


def _json_request(method: str, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = urllib_request.Request(
        url=url,
        method=method,
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib_request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        parsed = json.loads(body) if body else {}
        return {
            "status_code": int(getattr(resp, "status", 200)),
            "response": parsed,
        }


class AutomationHub:
    def __init__(self, *, store_path: Path, runs_path: Path, allowed_hosts: set[str] | None = None) -> None:
        self.store_path = Path(store_path)
        self.runs_path = Path(runs_path)
        self.allowed_hosts = {host.lower() for host in (allowed_hosts or set()) if host}

    def _ensure_parent_dirs(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.runs_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_rules(self) -> list[dict[str, Any]]:
        self._ensure_parent_dirs()
        if not self.store_path.exists():
            return []
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return payload if isinstance(payload, list) else []

    def _write_rules(self, rules: list[dict[str, Any]]) -> None:
        self._ensure_parent_dirs()
        self.store_path.write_text(json.dumps(rules, indent=2), encoding="utf-8")

    def _append_run(self, record: dict[str, Any]) -> None:
        self._ensure_parent_dirs()
        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _validate_target_url(self, target_url: str) -> None:
        parsed = urlparse(str(target_url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("target_url must be a valid http(s) URL")
        host = parsed.hostname.lower()
        if self.allowed_hosts and host not in self.allowed_hosts:
            raise ValueError("target_url host is not in the allowlist")

    def list_rules(self) -> list[dict[str, Any]]:
        return self._load_rules()

    def register_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        event = str(payload.get("event", "")).strip()
        target_url = str(payload.get("target_url", "")).strip()
        method = str(payload.get("method", "POST")).strip().upper()
        if not name:
            raise ValueError("name is required")
        if not event:
            raise ValueError("event is required")
        if method not in {"POST", "PUT", "PATCH"}:
            raise ValueError("method must be POST, PUT, or PATCH")
        self._validate_target_url(target_url)

        rules = self._load_rules()
        rule = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "event": event,
            "target_url": target_url,
            "method": method,
            "description": str(payload.get("description", "")).strip(),
            "enabled": bool(payload.get("enabled", True)),
            "static_headers": dict(payload.get("static_headers", {}) or {}),
            "static_payload": dict(payload.get("static_payload", {}) or {}),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        rules.append(rule)
        self._write_rules(rules)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        rules = self._load_rules()
        kept = [rule for rule in rules if str(rule.get("id")) != str(rule_id)]
        if len(kept) == len(rules):
            return False
        self._write_rules(kept)
        return True

    def emit_event(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not str(event or "").strip():
            raise ValueError("event is required")

        rules = [
            rule for rule in self._load_rules()
            if rule.get("enabled", True) and str(rule.get("event", "")).strip() == str(event).strip()
        ]
        results: list[dict[str, Any]] = []
        for rule in rules:
            body = {
                "event": event,
                "payload": dict(payload or {}),
                "metadata": dict(metadata or {}),
                "static_payload": dict(rule.get("static_payload", {}) or {}),
            }
            if dry_run:
                result = {
                    "rule_id": rule.get("id"),
                    "status": "dry_run",
                    "target_url": rule.get("target_url"),
                }
            else:
                try:
                    response = _json_request(
                        str(rule.get("method") or "POST"),
                        str(rule.get("target_url") or ""),
                        body,
                        dict(rule.get("static_headers", {}) or {}),
                    )
                    result = {
                        "rule_id": rule.get("id"),
                        "status": "sent",
                        "target_url": rule.get("target_url"),
                        **response,
                    }
                except urllib_error.URLError:
                    result = {
                        "rule_id": rule.get("id"),
                        "status": "error",
                        "target_url": rule.get("target_url"),
                    }
            results.append(result)

        record = {
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "matched_rules": len(rules),
            "dry_run": bool(dry_run),
            "results": results,
        }
        self._append_run(record)
        return record

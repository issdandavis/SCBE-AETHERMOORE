from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mail_ops = _load_module("test_proton_mail_ops", "scripts/system/proton_mail_ops.py")


class FakeImap:
    def __init__(self):
        self.created: list[str] = []
        self.copied: list[tuple[str, str]] = []
        self.stored: list[str] = []
        self.expunge_called = False

    def login(self, username: str, password: str):
        return "OK", [b"logged in"]

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Labels/Support"']

    def select(self, folder: str, readonly: bool = True):
        return "OK", [b"1"]

    def uid(self, command: str, *args):
        if command == "COPY":
            self.copied.append((args[0], args[1]))
            return "OK", [b""]
        if command == "STORE":
            self.stored.append((args[0], args[1], args[2]))
            return "OK", [b""]
        raise AssertionError(f"unexpected uid command: {command}")

    def create(self, folder: str):
        self.created.append(folder)
        return "OK", [b""]

    def expunge(self):
        self.expunge_called = True
        return "OK", [b""]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSmtp:
    def __init__(self):
        self.started_tls = False
        self.logged_in = None
        self.sent_to = None

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, username: str, password: str):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.sent_to = message["To"]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_doctor_payload_reports_missing_credentials(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "", "", "Labels")
    monkeypatch.setattr(mail_ops, "_probe_tcp", lambda host, port, timeout=1.5: False)
    monkeypatch.setattr(
        mail_ops,
        "_bridge_installation_candidates",
        lambda: ["C:/Program Files/Proton AG/Proton Mail Bridge/bridge.exe"],
    )

    payload = mail_ops.doctor(cfg)
    assert payload["ready"] is False
    assert payload["imap_reachable"] is False
    assert payload["smtp_reachable"] is False
    assert payload["config"]["password_present"] is False
    assert payload["bridge_installations"]
    assert payload["blockers"]


def test_load_config_uses_secret_store_fallback(monkeypatch) -> None:
    monkeypatch.delenv("PROTON_BRIDGE_USERNAME", raising=False)
    monkeypatch.delenv("PROTON_BRIDGE_PASSWORD", raising=False)

    def fake_get_secret(name: str, default: str = "") -> str:
        if name == "PROTON_BRIDGE_USERNAME":
            return "aethermoregames@pm.me"
        if name == "PROTON_BRIDGE_PASSWORD":
            return "bridge-password"
        return default

    monkeypatch.setattr(mail_ops, "get_secret", fake_get_secret)
    cfg = mail_ops.load_config()
    assert cfg.username == "aethermoregames@pm.me"
    assert cfg.password == "bridge-password"


def test_triage_prefers_order_bucket() -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "user", "pw", "Folders")
    summaries = [
        mail_ops.MessageSummary(
            uid="100",
            folder="INBOX",
            subject="Your Stripe receipt for checkout #1234",
            sender="billing@example.com",
            sender_address="billing@stripe.com",
            to="aethermoregames@pm.me",
            date="Tue, 24 Mar 2026 10:00:00 +0000",
            flags=[],
        )
    ]
    classified = [mail_ops._classify_message(item, cfg) for item in summaries][0]
    assert classified.classification == "orders"
    assert classified.suggested_target == "Folders/Orders"
    assert classified.suggested_action == "move"
    assert classified.confidence >= 0.9


def test_sweep_messages_groups_actions_and_targets(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "user", "pw", "Folders")
    monkeypatch.setattr(
        mail_ops,
        "triage_messages",
        lambda config, folder, limit: {
            "schema_version": "proton_mail_bridge_triage_v1",
            "generated_at": "2026-03-25T00:00:00Z",
            "folder": folder,
            "count": 2,
            "counts": {"admin": 1, "newsletter": 1},
            "messages": [
                {"uid": "1", "suggested_target": "Folders/Admin", "suggested_action": "move"},
                {"uid": "2", "suggested_target": "Archive", "suggested_action": "archive"},
            ],
            "lines": [],
        },
    )

    payload = mail_ops.sweep_messages(cfg, "INBOX", 25)
    assert payload["schema_version"] == "proton_mail_bridge_sweep_v1"
    assert payload["by_action"] == {"archive": 1, "move": 1}
    assert payload["by_target"] == {"Archive": 1, "Folders/Admin": 1}


def test_apply_triage_plan_dry_run_does_not_mutate(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "user", "pw", "Folders")
    fake = FakeImap()
    monkeypatch.setattr(mail_ops, "_connect_imap", lambda config: fake)
    monkeypatch.setattr(
        mail_ops,
        "triage_messages",
        lambda config, folder, limit: {
            "messages": [
                {
                    "uid": "1",
                    "subject": "Need help with setup",
                    "classification": "support",
                    "suggested_target": "Folders/Support",
                    "suggested_action": "move",
                }
            ]
        },
    )
    monkeypatch.setattr(mail_ops, "_audit", lambda event, payload: None)

    payload = mail_ops.apply_triage_plan(cfg, "INBOX", 10, execute=False)
    assert payload["move_count"] == 1
    assert payload["filtered_count"] == 0
    assert payload["moves"][0]["executed"] is False
    assert fake.created == []
    assert fake.copied == []
    assert fake.stored == []
    assert fake.expunge_called is False


def test_apply_triage_plan_filters_to_selected_targets(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "user", "pw", "Folders")
    fake = FakeImap()
    monkeypatch.setattr(mail_ops, "_connect_imap", lambda config: fake)
    monkeypatch.setattr(
        mail_ops,
        "triage_messages",
        lambda config, folder, limit: {
            "messages": [
                {
                    "uid": "1",
                    "subject": "GitHub alert",
                    "classification": "admin",
                    "suggested_target": "Folders/Admin",
                    "suggested_action": "move",
                },
                {
                    "uid": "2",
                    "subject": "Newsletter",
                    "classification": "newsletter",
                    "suggested_target": "Archive",
                    "suggested_action": "archive",
                },
            ]
        },
    )
    monkeypatch.setattr(mail_ops, "_audit", lambda event, payload: None)

    payload = mail_ops.apply_triage_plan(cfg, "INBOX", 10, execute=False, only_targets={"Folders/Admin"})
    assert payload["move_count"] == 1
    assert payload["filtered_count"] == 1
    assert payload["only_targets"] == ["Folders/Admin"]
    assert payload["moves"][0]["target"] == "Folders/Admin"
    assert fake.copied == []


def test_apply_triage_plan_execute_marks_deleted_flag(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "user", "pw", "Folders")
    fake = FakeImap()
    monkeypatch.setattr(mail_ops, "_connect_imap", lambda config: fake)
    monkeypatch.setattr(
        mail_ops,
        "triage_messages",
        lambda config, folder, limit: {
            "messages": [
                {
                    "uid": "7",
                    "subject": "GitHub alert",
                    "classification": "admin",
                    "suggested_target": "Folders/Admin",
                    "suggested_action": "move",
                }
            ]
        },
    )
    monkeypatch.setattr(mail_ops, "_audit", lambda event, payload: None)

    payload = mail_ops.apply_triage_plan(cfg, "INBOX", 10, execute=True, only_targets={"Folders/Admin"})
    assert payload["move_count"] == 1
    assert fake.copied == [("7", "Folders/Admin")]
    assert fake.stored == [("7", "+FLAGS", r"\Deleted")]
    assert fake.expunge_called is True


def test_send_mail_execute_uses_authenticated_bridge_smtp(monkeypatch) -> None:
    cfg = mail_ops.BridgeConfig("127.0.0.1", 1143, 1025, "aethermoregames@pm.me", "bridge-password", "Folders")
    fake = FakeSmtp()
    monkeypatch.setattr(mail_ops, "_connect_smtp", lambda config: fake)
    monkeypatch.setattr(mail_ops, "_audit", lambda event, payload: None)

    payload = mail_ops.send_mail(cfg, "buyer@example.com", "Hello", "World", execute=True)
    assert payload["status"] == "sent"
    assert fake.sent_to == "buyer@example.com"


def test_store_credentials_persists_bridge_secrets(monkeypatch) -> None:
    writes: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mail_ops, "set_secret", lambda name, value, note="": writes.append((name, value, note)))
    monkeypatch.setattr(mail_ops, "_audit", lambda event, payload: None)

    payload = mail_ops.store_credentials("aethermoregames@pm.me", "bridge-password")
    assert payload["status"] == "stored"
    assert writes == [
        ("PROTON_BRIDGE_USERNAME", "aethermoregames@pm.me", "Proton Mail Bridge username"),
        ("PROTON_BRIDGE_PASSWORD", "bridge-password", "Proton Mail Bridge password"),
    ]

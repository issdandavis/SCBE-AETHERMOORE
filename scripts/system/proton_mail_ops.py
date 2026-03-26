#!/usr/bin/env python3
"""Secure local Proton Mail Bridge operations for AI-assisted inbox work.

Design goals:
- Local only: talks to Proton Mail Bridge over localhost IMAP/SMTP.
- Dry-run first: read-only by default, mutations require explicit flags.
- AI-friendly: emits compact JSON summaries instead of dumping raw mailbox state.
- Auditable: every mutating or planning action appends a JSONL event.

Environment:
- PROTON_BRIDGE_HOST=127.0.0.1
- PROTON_BRIDGE_IMAP_PORT=1143
- PROTON_BRIDGE_SMTP_PORT=1025
- PROTON_BRIDGE_USERNAME=<Bridge mailbox username>
- PROTON_BRIDGE_PASSWORD=<Bridge mailbox password>
- PROTON_BRIDGE_FOLDER_PREFIX=Labels
"""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import smtplib
import socket
import ssl
import sys
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.utils import parseaddr
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.security.secret_store import get_secret, set_secret  # noqa: E402

ARTIFACT_DIR = REPO_ROOT / "artifacts" / "mail"
AUDIT_LOG = ARTIFACT_DIR / "proton_mail_ops.jsonl"
RULES_PATH = REPO_ROOT / "config" / "proton_mail_rules.json"
DEFAULT_ALLOWED_TARGETS = (
    "Support",
    "Orders",
    "Access Keys",
    "Delivery Failures",
    "Sales",
    "Partnerships",
    "Admin",
    "AI Review",
    "Urgent",
)


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    imap_port: int
    smtp_port: int
    username: str
    password: str
    folder_prefix: str

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    @property
    def redacted(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "imap_port": self.imap_port,
            "smtp_port": self.smtp_port,
            "username": self.username,
            "password_present": bool(self.password),
            "folder_prefix": self.folder_prefix,
        }


@dataclass(frozen=True)
class MessageSummary:
    uid: str
    folder: str
    subject: str
    sender: str
    sender_address: str
    to: str
    date: str
    flags: list[str]
    list_id: str = ""
    list_unsubscribe: str = ""
    auto_submitted: str = ""
    classification: str = "unclassified"
    confidence: float = 0.0
    rationale: str = ""
    suggested_target: str = ""
    suggested_action: str = "move"



def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")



def load_config() -> BridgeConfig:
    folder_prefix = os.getenv("PROTON_BRIDGE_FOLDER_PREFIX", "")
    if not folder_prefix and RULES_PATH.exists():
        try:
            payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
            folder_prefix = str(payload.get("folder_prefix", ""))
        except json.JSONDecodeError:
            folder_prefix = ""
    username = os.getenv("PROTON_BRIDGE_USERNAME", "").strip() or get_secret("PROTON_BRIDGE_USERNAME", "").strip()
    password = os.getenv("PROTON_BRIDGE_PASSWORD", "").strip() or get_secret("PROTON_BRIDGE_PASSWORD", "").strip()
    return BridgeConfig(
        host=os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1"),
        imap_port=int(os.getenv("PROTON_BRIDGE_IMAP_PORT", "1143")),
        smtp_port=int(os.getenv("PROTON_BRIDGE_SMTP_PORT", "1025")),
        username=username,
        password=password,
        folder_prefix=folder_prefix or "Folders",
    )



def _emit(payload: dict[str, Any], json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        for line in payload.get("lines", []):
            print(line)
    return 0



def _audit(event: str, payload: dict[str, Any]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": _now_iso(), "event": event, **payload}
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")



def _probe_tcp(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False



def _bridge_installation_candidates() -> list[str]:
    candidates = [
        Path("C:/Program Files/Proton AG/Proton Mail Bridge/bridge.exe"),
        Path("C:/Program Files/Proton AG/Proton Mail Bridge/bridge-gui.exe"),
    ]
    return [str(path) for path in candidates if path.exists()]


def _load_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return {}
    try:
        payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}



def doctor(config: BridgeConfig) -> dict[str, Any]:
    imap_reachable = _probe_tcp(config.host, config.imap_port)
    smtp_reachable = _probe_tcp(config.host, config.smtp_port)
    ready = config.has_credentials and imap_reachable and smtp_reachable
    blockers: list[str] = []
    if not config.has_credentials:
        blockers.append("Bridge credentials are not set in PROTON_BRIDGE_USERNAME / PROTON_BRIDGE_PASSWORD.")
    if not imap_reachable:
        blockers.append(f"IMAP port {config.host}:{config.imap_port} is not reachable.")
    if not smtp_reachable:
        blockers.append(f"SMTP port {config.host}:{config.smtp_port} is not reachable.")
    payload = {
        "schema_version": "proton_mail_bridge_doctor_v1",
        "generated_at": _now_iso(),
        "config": config.redacted,
        "bridge_installations": _bridge_installation_candidates(),
        "imap_reachable": imap_reachable,
        "smtp_reachable": smtp_reachable,
        "ready": ready,
        "blockers": blockers,
        "lines": [
            "Proton Mail Bridge Doctor",
            "=" * 32,
            f"ready: {'yes' if ready else 'no'}",
            f"imap reachable: {'yes' if imap_reachable else 'no'}",
            f"smtp reachable: {'yes' if smtp_reachable else 'no'}",
            f"credentials present: {'yes' if config.has_credentials else 'no'}",
        ]
        + (["blockers:"] + [f"  - {item}" for item in blockers] if blockers else ["no blockers detected"]),
    }
    return payload



def _connect_imap(config: BridgeConfig) -> imaplib.IMAP4:
    if not config.has_credentials:
        raise RuntimeError("Bridge credentials are required. Set PROTON_BRIDGE_USERNAME and PROTON_BRIDGE_PASSWORD.")
    client = imaplib.IMAP4(config.host, config.imap_port)
    client.login(config.username, config.password)
    return client



def _connect_smtp(config: BridgeConfig) -> smtplib.SMTP:
    if not config.has_credentials:
        raise RuntimeError("Bridge credentials are required. Set PROTON_BRIDGE_USERNAME and PROTON_BRIDGE_PASSWORD.")
    client = smtplib.SMTP(config.host, config.smtp_port, timeout=10)
    client.starttls(context=ssl.create_default_context())
    client.login(config.username, config.password)
    return client



def _decode_imap_value(raw: bytes | str | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw



def list_folders(config: BridgeConfig) -> dict[str, Any]:
    with _connect_imap(config) as client:
        status, data = client.list()
        if status != "OK":
            raise RuntimeError("Unable to list folders from Proton Bridge.")
    folders: list[str] = []
    for row in data:
        text = _decode_imap_value(row)
        match = re.search(r'"([^"]+)"\s*$', text)
        folders.append(match.group(1) if match else text.split()[-1])
    return {
        "schema_version": "proton_mail_bridge_folders_v1",
        "generated_at": _now_iso(),
        "count": len(folders),
        "folders": folders,
        "lines": ["Folders:"] + [f"  - {name}" for name in folders],
    }



def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    return str(email.header.make_header(email.header.decode_header(value)))



def _parse_flags(fetch_meta: bytes | str | None) -> list[str]:
    text = _decode_imap_value(fetch_meta)
    match = re.search(r"FLAGS \(([^)]*)\)", text)
    if not match:
        return []
    return [flag for flag in match.group(1).split() if flag]



def fetch_summaries(config: BridgeConfig, folder: str, limit: int = 25) -> list[MessageSummary]:
    with _connect_imap(config) as client:
        status, _ = client.select(folder, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select folder: {folder}")
        status, data = client.uid("search", None, "ALL")
        if status != "OK":
            raise RuntimeError(f"Unable to search folder: {folder}")
        uids = [uid for uid in _decode_imap_value(data[0]).split() if uid]
        selected = uids[-limit:]
        summaries: list[MessageSummary] = []
        for uid in reversed(selected):
            status, rows = client.uid(
                "fetch",
                uid,
                "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE LIST-ID LIST-UNSUBSCRIBE AUTO-SUBMITTED)] FLAGS)",
            )
            if status != "OK" or not rows:
                continue
            header_bytes = b""
            meta = None
            for row in rows:
                if isinstance(row, tuple):
                    meta = row[0]
                    header_bytes = row[1] or b""
                    break
            msg = BytesParser(policy=default).parsebytes(header_bytes)
            sender_text = _decode_header(msg.get("From"))
            sender_address = parseaddr(sender_text)[1].lower()
            summaries.append(
                MessageSummary(
                    uid=uid,
                    folder=folder,
                    subject=_decode_header(msg.get("Subject")),
                    sender=sender_text,
                    sender_address=sender_address,
                    to=_decode_header(msg.get("To")),
                    date=_decode_header(msg.get("Date")),
                    flags=_parse_flags(meta),
                    list_id=_decode_header(msg.get("List-Id")),
                    list_unsubscribe=_decode_header(msg.get("List-Unsubscribe")),
                    auto_submitted=_decode_header(msg.get("Auto-Submitted")),
                )
            )
    return summaries



def _route_target(config: BridgeConfig, target: str, action: str) -> str:
    if action == "archive":
        return "Archive"
    if action == "trash":
        return "Trash"
    if "/" in target:
        return target
    return _qualify_target(config, target)


def _apply_classification(
    summary: MessageSummary,
    config: BridgeConfig,
    classification: str,
    confidence: float,
    target: str,
    rationale: str,
    action: str,
) -> MessageSummary:
    return MessageSummary(
        uid=summary.uid,
        folder=summary.folder,
        subject=summary.subject,
        sender=summary.sender,
        sender_address=summary.sender_address,
        to=summary.to,
        date=summary.date,
        flags=summary.flags,
        list_id=summary.list_id,
        list_unsubscribe=summary.list_unsubscribe,
        auto_submitted=summary.auto_submitted,
        classification=classification,
        confidence=confidence,
        rationale=rationale,
        suggested_target=_route_target(config, target, action),
        suggested_action=action,
    )


def _classify_message(summary: MessageSummary, config: BridgeConfig) -> MessageSummary:
    text = (
        f"{summary.subject} {summary.sender} {summary.to} "
        f"{summary.list_id} {summary.list_unsubscribe} {summary.auto_submitted}"
    ).lower()
    rules = _load_rules()
    sender_domain = summary.sender_address.split("@", 1)[1] if "@" in summary.sender_address else ""

    for rule in rules.get("sender_domain_rules", []):
        if sender_domain == str(rule.get("domain", "")).lower():
            return _apply_classification(
                summary,
                config,
                classification=str(rule.get("classification", "ai_review")),
                confidence=float(rule.get("confidence", 0.9)),
                target=str(rule.get("target", "AI Review")),
                rationale=str(rule.get("rationale", "configured sender domain rule")),
                action=str(rule.get("action", "move")),
            )

    for rule in rules.get("subject_rules", []):
        needles = [str(item).lower() for item in rule.get("contains", [])]
        if any(needle in text for needle in needles):
            return _apply_classification(
                summary,
                config,
                classification=str(rule.get("classification", "ai_review")),
                confidence=float(rule.get("confidence", 0.8)),
                target=str(rule.get("target", "AI Review")),
                rationale=str(rule.get("rationale", "configured subject rule")),
                action=str(rule.get("action", "move")),
            )

    if summary.list_unsubscribe or summary.list_id:
        return _apply_classification(
            summary,
            config,
            classification="newsletter",
            confidence=0.85,
            target="Archive",
            rationale="mailing-list headers present",
            action="archive",
        )

    rules_table: list[tuple[str, tuple[str, ...], float, str, str]] = [
        ("delivery_failure", ("delivery", "undeliver", "mail delivery", "bounce", "returned to sender"), 0.97, "Delivery Failures", "delivery-status markers in subject/header"),
        ("access_keys", ("license", "api key", "access key", "activation", "download link"), 0.93, "Access Keys", "access or key distribution markers"),
        ("orders", ("order", "receipt", "invoice", "payment", "checkout", "gumroad", "stripe", "shopify"), 0.9, "Orders", "commerce markers"),
        ("support", ("help", "issue", "bug", "support", "can't", "cannot", "problem", "trouble"), 0.84, "Support", "support/problem markers"),
        ("partnerships", ("partnership", "collab", "collaboration", "meeting", "demo", "proposal", "investor"), 0.82, "Partnerships", "business development markers"),
        ("admin", ("github", "notification", "ci", "workflow", "build failed", "security alert"), 0.8, "Admin", "ops/admin markers"),
    ]
    for label, needles, confidence, target, rationale in rules_table:
        if any(needle in text for needle in needles):
            return _apply_classification(summary, config, label, confidence, target, rationale, "move")

    return _apply_classification(
        summary,
        config,
        classification="ai_review",
        confidence=0.55,
        target="AI Review",
        rationale="no deterministic rule matched; route for supervised review",
        action="move",
    )



def _qualify_target(config: BridgeConfig, label: str) -> str:
    prefix = config.folder_prefix.strip().strip("/")
    return f"{prefix}/{label}" if prefix else label



def triage_messages(config: BridgeConfig, folder: str, limit: int) -> dict[str, Any]:
    summaries = [_classify_message(item, config) for item in fetch_summaries(config, folder, limit)]
    counts: dict[str, int] = {}
    for item in summaries:
        counts[item.classification] = counts.get(item.classification, 0) + 1
    return {
        "schema_version": "proton_mail_bridge_triage_v1",
        "generated_at": _now_iso(),
        "folder": folder,
        "count": len(summaries),
        "counts": counts,
        "messages": [asdict(item) for item in summaries],
        "lines": [f"Triage for {folder}: {len(summaries)} message(s)"]
        + [f"  {name}: {count}" for name, count in sorted(counts.items())],
    }



def _ensure_target_allowed(target: str, allowed_targets: tuple[str, ...], config: BridgeConfig) -> None:
    allowed = {_qualify_target(config, label) for label in allowed_targets}
    if target not in allowed:
        raise RuntimeError(f"Target folder '{target}' is not in the allowlist: {sorted(allowed)}")



def apply_triage_plan(
    config: BridgeConfig,
    folder: str,
    limit: int,
    execute: bool,
    only_targets: set[str] | None = None,
) -> dict[str, Any]:
    plan = triage_messages(config, folder, limit)
    moves: list[dict[str, Any]] = []
    filtered_count = 0
    with _connect_imap(config) as client:
        status, _ = client.select(folder, readonly=not execute)
        if status != "OK":
            raise RuntimeError(f"Unable to select folder: {folder}")
        for item in plan["messages"]:
            target = item["suggested_target"]
            if only_targets and target not in only_targets:
                filtered_count += 1
                continue
            action = str(item.get("suggested_action", "move"))
            if action == "move":
                _ensure_target_allowed(target, DEFAULT_ALLOWED_TARGETS, config)
            move_record = {
                "uid": item["uid"],
                "subject": item["subject"],
                "classification": item["classification"],
                "target": target,
                "action": action,
                "executed": False,
            }
            if execute:
                if action == "move":
                    client.create(target)
                copy_status, _ = client.uid("COPY", item["uid"], target)
                if copy_status == "OK":
                    client.uid("STORE", item["uid"], "+FLAGS", r"\Deleted")
                    move_record["executed"] = True
                else:
                    move_record["error"] = f"COPY failed with status {copy_status}"
            moves.append(move_record)
        if execute:
            client.expunge()
    _audit(
        "triage_apply",
        {
            "folder": folder,
            "limit": limit,
            "execute": execute,
            "filtered_count": filtered_count,
            "only_targets": sorted(only_targets) if only_targets else [],
            "move_count": len(moves),
            "moves": moves,
        },
    )
    return {
        "schema_version": "proton_mail_bridge_apply_v1",
        "generated_at": _now_iso(),
        "folder": folder,
        "execute": execute,
        "filtered_count": filtered_count,
        "only_targets": sorted(only_targets) if only_targets else [],
        "move_count": len(moves),
        "moves": moves,
        "lines": [
            f"Applied triage plan for {folder}: {len(moves)} move(s), filtered={filtered_count}, execute={'yes' if execute else 'no'}"
        ],
    }


def sweep_messages(config: BridgeConfig, folder: str, limit: int) -> dict[str, Any]:
    payload = triage_messages(config, folder, limit)
    by_target: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for item in payload["messages"]:
        target = str(item.get("suggested_target", ""))
        action = str(item.get("suggested_action", "move"))
        by_target[target] = by_target.get(target, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1
    payload["schema_version"] = "proton_mail_bridge_sweep_v1"
    payload["by_target"] = by_target
    payload["by_action"] = by_action
    payload["lines"] = [f"Sweep for {folder}: {payload['count']} message(s)"] + [
        f"  action {name}: {count}" for name, count in sorted(by_action.items())
    ] + [
        f"  target {name}: {count}" for name, count in sorted(by_target.items())
    ]
    return payload



def send_mail(config: BridgeConfig, to: str, subject: str, body: str, execute: bool) -> dict[str, Any]:
    message = EmailMessage()
    message["From"] = config.username
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    status = "dry_run"
    if execute:
        with _connect_smtp(config) as client:
            client.send_message(message)
        status = "sent"
    _audit(
        "send_mail",
        {
            "to": to,
            "subject": subject,
            "execute": execute,
            "status": status,
        },
    )
    return {
        "schema_version": "proton_mail_bridge_send_v1",
        "generated_at": _now_iso(),
        "to": to,
        "subject": subject,
        "execute": execute,
        "status": status,
        "lines": [f"Send status: {status} -> {to}"],
    }



def store_credentials(username: str, password: str) -> dict[str, Any]:
    clean_username = username.strip()
    clean_password = password.strip()
    if not clean_username or not clean_password:
        raise RuntimeError("Both username and password are required to store Proton Bridge credentials.")
    set_secret("PROTON_BRIDGE_USERNAME", clean_username, note="Proton Mail Bridge username")
    set_secret("PROTON_BRIDGE_PASSWORD", clean_password, note="Proton Mail Bridge password")
    _audit(
        "store_credentials",
        {
            "username": clean_username,
            "password_present": True,
        },
    )
    return {
        "schema_version": "proton_mail_bridge_store_credentials_v1",
        "generated_at": _now_iso(),
        "username": clean_username,
        "password_present": True,
        "status": "stored",
        "lines": [f"Stored Proton Bridge credentials for {clean_username} in the local secret store."],
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    return _emit(doctor(load_config()), args.json)



def cmd_folders(args: argparse.Namespace) -> int:
    return _emit(list_folders(load_config()), args.json)



def cmd_inbox(args: argparse.Namespace) -> int:
    payload = {
        "schema_version": "proton_mail_bridge_inbox_v1",
        "generated_at": _now_iso(),
        "folder": args.folder,
        "count": 0,
        "messages": [],
        "lines": [],
    }
    messages = fetch_summaries(load_config(), args.folder, args.limit)
    payload["count"] = len(messages)
    payload["messages"] = [asdict(item) for item in messages]
    payload["lines"] = [f"Inbox summaries for {args.folder}: {len(messages)}"] + [
        f"  {item.uid}: {item.subject} <- {item.sender}" for item in messages
    ]
    return _emit(payload, args.json)



def cmd_triage(args: argparse.Namespace) -> int:
    return _emit(triage_messages(load_config(), args.folder, args.limit), args.json)


def cmd_sweep(args: argparse.Namespace) -> int:
    return _emit(sweep_messages(load_config(), args.folder, args.limit), args.json)


def cmd_apply(args: argparse.Namespace) -> int:
    only_targets = set(args.only_target or [])
    return _emit(
        apply_triage_plan(load_config(), args.folder, args.limit, execute=args.execute, only_targets=only_targets or None),
        args.json,
    )



def cmd_send(args: argparse.Namespace) -> int:
    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    if not body:
        raise SystemExit("Provide --body or --body-file.")
    return _emit(send_mail(load_config(), args.to, args.subject, body, execute=args.execute), args.json)


def cmd_store_credentials(args: argparse.Namespace) -> int:
    return _emit(store_credentials(args.username, args.password), args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Secure Proton Mail Bridge operations for local AI mail workflows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    doctor_cmd = sub.add_parser("doctor", help="Check Bridge install, ports, and credential readiness")
    add_common_flags(doctor_cmd)
    doctor_cmd.set_defaults(func=cmd_doctor)

    folders_cmd = sub.add_parser("folders", help="List folders visible through Proton Bridge")
    add_common_flags(folders_cmd)
    folders_cmd.set_defaults(func=cmd_folders)

    store_cmd = sub.add_parser("store-credentials", help="Store Bridge credentials in the local encrypted secret store")
    add_common_flags(store_cmd)
    store_cmd.add_argument("--username", required=True)
    store_cmd.add_argument("--password", required=True)
    store_cmd.set_defaults(func=cmd_store_credentials)

    inbox_cmd = sub.add_parser("inbox", help="List compact header-only inbox summaries")
    add_common_flags(inbox_cmd)
    inbox_cmd.add_argument("--folder", default="INBOX")
    inbox_cmd.add_argument("--limit", type=int, default=25)
    inbox_cmd.set_defaults(func=cmd_inbox)

    triage_cmd = sub.add_parser("triage", help="Plan deterministic triage for the selected folder")
    add_common_flags(triage_cmd)
    triage_cmd.add_argument("--folder", default="INBOX")
    triage_cmd.add_argument("--limit", type=int, default=25)
    triage_cmd.set_defaults(func=cmd_triage)

    sweep_cmd = sub.add_parser("sweep", help="Compact anti-flood report with actions and targets")
    add_common_flags(sweep_cmd)
    sweep_cmd.add_argument("--folder", default="INBOX")
    sweep_cmd.add_argument("--limit", type=int, default=100)
    sweep_cmd.set_defaults(func=cmd_sweep)

    apply_cmd = sub.add_parser("apply", help="Apply the triage plan; dry-run unless --execute is set")
    add_common_flags(apply_cmd)
    apply_cmd.add_argument("--folder", default="INBOX")
    apply_cmd.add_argument("--limit", type=int, default=25)
    apply_cmd.add_argument("--only-target", action="append", default=[], help="Apply only messages whose suggested target matches this value")
    apply_cmd.add_argument("--execute", action="store_true", help="Actually move messages")
    apply_cmd.set_defaults(func=cmd_apply)

    send_cmd = sub.add_parser("send", help="Send a mail via Proton Bridge SMTP; dry-run unless --execute is set")
    add_common_flags(send_cmd)
    send_cmd.add_argument("--to", required=True)
    send_cmd.add_argument("--subject", required=True)
    send_cmd.add_argument("--body", default="")
    send_cmd.add_argument("--body-file", default="")
    send_cmd.add_argument("--execute", action="store_true", help="Actually send the mail")
    send_cmd.set_defaults(func=cmd_send)
    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Provision a browser-backed Colab worker lease with HYDRA relay packets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from urllib.parse import urlparse

from scripts.system import colab_workflow_catalog as catalog
from scripts.system import crosstalk_relay as relay


REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_url(raw_url: str) -> str:
    """Strip query string and fragment from a URL to avoid leaking secrets."""
    parsed = urlparse(raw_url)
    return parsed._replace(query="", fragment="").geturl()
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "colab_workers"
DEFAULT_PROFILE_DIR = Path.home() / ".scbe-playwright-colab"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_str(value: datetime | None = None) -> str:
    stamp = value or _utc_now()
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "worker"


def _load_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc
    return sync_playwright


def build_worker_lease(
    *,
    worker_id: str,
    notebook_name: str,
    provider: str = "colab",
    resource_class: str = "browser-colab",
    lease_seconds: int = 3600,
    claimed_at: datetime | None = None,
) -> Dict[str, Any]:
    claimed = claimed_at or _utc_now()
    lease_id = f"lease-{_slug(worker_id)}-{_slug(notebook_name)}-{claimed.strftime('%Y%m%d%H%M%S')}"
    expires = claimed + timedelta(seconds=max(0, int(lease_seconds)))
    return {
        "lease_id": lease_id,
        "owner": worker_id,
        "provider": provider,
        "resource_class": resource_class,
        "lease_seconds": int(lease_seconds),
        "claimed_at_utc": _utc_str(claimed),
        "expires_at_utc": _utc_str(expires),
    }


def _state_from_page(url: str, title: str) -> str:
    lowered_url = url.lower()
    lowered_title = title.lower()
    if "accounts.google.com" in lowered_url:
        return "auth_required"
    if "choose an account" in lowered_title or "sign in" in lowered_title:
        return "auth_required"
    if "colab" in lowered_url or "colab" in lowered_title:
        return "notebook_open"
    return "unknown"


def _probe_colab_runtime(page) -> Dict[str, Any]:
    return page.evaluate(
        """
() => {
  const usage = document.querySelector('colab-usage-display');
  const machine = document.querySelector('colab-machine-type');
  const buttons = Array.from(document.querySelectorAll('button'))
    .map((btn) => (btn.innerText || btn.textContent || '').trim())
    .filter(Boolean);
  const connectVisible = buttons.some((text) => {
    const lowered = text.toLowerCase();
    return lowered === 'connect' || lowered === 'reconnect' || lowered.includes('connect');
  });
  return {
    notebook_loaded: document.querySelectorAll('.cell').length > 0,
    usage_visible: !!usage,
    usage_text: usage ? (usage.innerText || usage.textContent || '').trim().slice(0, 240) : '',
    machine_type: machine ? (machine.innerText || machine.textContent || '').trim().slice(0, 120) : '',
    connect_button_visible: connectVisible,
    button_samples: buttons.slice(0, 12),
  };
}
"""
    )


def _derive_runtime_state(base_state: str, runtime_probe: Dict[str, Any]) -> str:
    if base_state == "auth_required":
        return base_state
    if runtime_probe.get("usage_visible"):
        return "runtime_connected"
    if runtime_probe.get("connect_button_visible"):
        return "runtime_disconnected"
    return base_state


def _layer14_from_state(state: str, title: str, url: str) -> Dict[str, Any]:
    if state == "runtime_connected":
        energy = 1.0
        flux = 0.0
        hf_ratio = 0.0
        stability = 1.0
    elif state == "runtime_disconnected":
        energy = 0.72
        flux = 0.28
        hf_ratio = 0.08
        stability = 0.72
    elif state == "notebook_open":
        energy = 0.86
        flux = 0.14
        hf_ratio = 0.04
        stability = 0.86
    elif state == "auth_required":
        energy = 0.45
        flux = 0.55
        hf_ratio = 0.4
        stability = 0.55
    else:
        energy = 0.65
        flux = 0.25
        hf_ratio = 0.1
        stability = 0.7
    return {
        "energy": round(energy, 4),
        "centroid": round(energy, 4),
        "flux": round(flux, 4),
        "hf_ratio": round(hf_ratio, 4),
        "stability": round(stability, 4),
        "verification_score": round(stability, 4),
        "anomaly_ratio": round(1.0 - stability, 4),
        "signal_class": state,
        "channel": "layer14-comms",
        "summary": f"{title or 'untitled'} @ {url}",
    }


def _packet_rails(
    notebook: Dict[str, Any],
    *,
    state: str,
    artifact_path: str,
    current_url: str,
    title: str,
    dry_run: bool,
) -> Dict[str, list[Dict[str, Any]]]:
    positive = [
        {"type": "navigate", "target": notebook["colab_url"]},
        {"type": "profile_dir", "target": artifact_path},
    ]
    friction: list[Dict[str, Any]] = []
    contradictions: list[Dict[str, Any]] = []
    if dry_run:
        friction.append({"type": "dry_run", "message": "browser launch skipped"})
    if state == "auth_required":
        contradictions.append({"type": "auth_required", "url": current_url, "title": title})
    if state == "runtime_disconnected":
        friction.append({"type": "runtime_connect_needed", "url": current_url, "title": title})
    confirmations = [
        {"type": "state", "value": state},
        {"type": "title", "value": title},
        {"type": "url", "value": current_url},
        {"type": "artifact_path", "value": artifact_path},
    ]
    return {"P+": positive, "P-": friction, "D+": confirmations, "D-": contradictions}


def _emit_packet(
    *,
    packet_class: str,
    sender: str,
    recipient: str,
    intent: str,
    task_id: str,
    summary: str,
    mission_id: str,
    worker_id: str,
    lease: Dict[str, Any],
    rails: Dict[str, Any],
    layer14: Dict[str, Any],
    proof: list[str],
    next_action: str,
    status: str = "in_progress",
) -> Dict[str, Any]:
    return relay.emit_packet(
        sender=sender,
        recipient=recipient,
        intent=intent,
        task_id=task_id,
        summary=summary,
        status=status,
        proof=proof,
        next_action=next_action,
        packet_class=packet_class,
        mission_id=mission_id,
        worker_id=worker_id,
        lease=lease,
        rails=rails,
        layer14=layer14,
    )


def provision_colab_worker(
    *,
    notebook_query: str,
    mission_id: str,
    worker_id: str,
    session_id: str,
    recipient: str,
    sender: str,
    profile_dir: Path,
    artifact_root: Path,
    lease_seconds: int,
    headless: bool,
    keep_open: bool,
    timeout_ms: int,
    dry_run: bool,
) -> Dict[str, Any]:
    notebook = catalog.resolve_notebook_payload(notebook_query)
    lease = build_worker_lease(worker_id=worker_id, notebook_name=notebook["name"], lease_seconds=lease_seconds)
    artifact_dir = artifact_root / mission_id / worker_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "colab_worker_session.json"

    claim_packet = _emit_packet(
        packet_class="governance",
        sender=sender,
        recipient=recipient,
        intent="claim_colab_worker",
        task_id=f"COLAB-WORKER-{notebook['name']}",
        summary=f"Claiming Colab worker lease for {notebook['name']}.",
        mission_id=mission_id,
        worker_id=worker_id,
        lease=lease,
        rails={"P+": [{"type": "claim_lease", "notebook": notebook["name"]}], "P-": [], "D+": [], "D-": []},
        layer14={
            "energy": 0.2,
            "centroid": 0.2,
            "flux": 0.0,
            "hf_ratio": 0.0,
            "stability": 1.0,
            "verification_score": 1.0,
            "anomaly_ratio": 0.0,
            "signal_class": "lease_claimed",
            "channel": "layer14-comms",
            "summary": notebook["colab_url"],
        },
        proof=[notebook["path"]],
        next_action="Launch persistent Chromium context for Colab.",
    )

    title = "dry-run"
    current_url = notebook["colab_url"]
    state = "dry_run"
    screenshot_path = None
    runtime_probe: Dict[str, Any] = {}

    if not dry_run:
        sync_playwright = _load_sync_playwright()
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(notebook["colab_url"], wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(4000)
                title = page.title()
                current_url = page.url
                state = _state_from_page(current_url, title)
                runtime_probe = _probe_colab_runtime(page)
                state = _derive_runtime_state(state, runtime_probe)
                screenshot_path = artifact_dir / "colab_worker_page.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                if keep_open:  # pragma: no cover
                    input("Colab worker browser is open. Press Enter to close... ")
            finally:
                context.close()

    layer14 = _layer14_from_state(state, title, current_url)
    rails = _packet_rails(
        notebook,
        state=state,
        artifact_path=str(artifact_path),
        current_url=current_url,
        title=title,
        dry_run=dry_run,
    )

    internal_packet = _emit_packet(
        packet_class="internal",
        sender=sender,
        recipient=recipient,
        intent="colab_worker_ready",
        task_id=f"COLAB-WORKER-{notebook['name']}",
        summary=f"Colab worker {worker_id} reached state {state}.",
        mission_id=mission_id,
        worker_id=worker_id,
        lease=lease,
        rails=rails,
        layer14=layer14,
        proof=[notebook["colab_url"]],
        next_action="Attach workload or authenticate if required.",
        status="ready" if state == "notebook_open" else "attention",
    )

    evidence_proof = [str(artifact_path)]
    if screenshot_path is not None:
        evidence_proof.append(str(screenshot_path))
    evidence_packet = _emit_packet(
        packet_class="evidence",
        sender=sender,
        recipient=recipient,
        intent="colab_worker_evidence",
        task_id=f"COLAB-WORKER-{notebook['name']}",
        summary=f"Captured Colab worker evidence for {notebook['name']}.",
        mission_id=mission_id,
        worker_id=worker_id,
        lease=lease,
        rails=rails,
        layer14=layer14,
        proof=evidence_proof,
        next_action="Use artifact path for replay or handoff.",
        status="logged",
    )

    artifact = {
        "mission_id": mission_id,
        "worker_id": worker_id,
        "session_id": session_id,
        "sender": sender,
        "recipient": recipient,
        "lease": lease,
        "notebook": notebook,
        "state": state,
        "title": title,
        "current_url": current_url,
        "profile_dir": str(profile_dir),
        "headless": headless,
        "dry_run": dry_run,
        "artifact_path": str(artifact_path),
        "screenshot_path": str(screenshot_path) if screenshot_path is not None else None,
        "runtime_probe": runtime_probe,
        "packets": {
            "claim": claim_packet["packet_id"],
            "internal": internal_packet["packet_id"],
            "evidence": evidence_packet["packet_id"],
        },
        "layer14": layer14,
        "rails": rails,
        "claimed_at_utc": lease["claimed_at_utc"],
    }
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision a browser-backed Colab worker lease.")
    parser.add_argument("--notebook", required=True, help="Notebook name or alias from the Colab catalog.")
    parser.add_argument("--mission-id", default="", help="Mission identifier.")
    parser.add_argument("--worker-id", default="", help="Worker identifier.")
    parser.add_argument("--session-id", default="", help="Session identifier.")
    parser.add_argument("--recipient", default="agent.claude", help="Cross-talk recipient.")
    parser.add_argument("--sender", default="agent.codex", help="Cross-talk sender.")
    parser.add_argument(
        "--profile-dir", default=str(DEFAULT_PROFILE_DIR), help="Persistent Chromium profile directory."
    )
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT), help="Artifact root directory.")
    parser.add_argument("--lease-seconds", type=int, default=3600, help="Lease duration in seconds.")
    parser.add_argument("--timeout-ms", type=int, default=90000, help="Page load timeout.")
    parser.add_argument("--headless", action="store_true", help="Launch browser headless.")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Launch browser with UI.")
    parser.add_argument("--keep-open", action="store_true", help="Keep the browser open until Enter is pressed.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Resolve notebook and emit packets without launching the browser."
    )
    parser.set_defaults(headless=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    mission_id = args.mission_id.strip() or f"colab-mission-{_utc_now().strftime('%Y%m%d%H%M%S')}"
    worker_id = args.worker_id.strip() or f"worker-colab-{_slug(args.notebook)}"
    session_id = args.session_id.strip() or f"{worker_id}-session"
    artifact = provision_colab_worker(
        notebook_query=args.notebook,
        mission_id=mission_id,
        worker_id=worker_id,
        session_id=session_id,
        recipient=args.recipient,
        sender=args.sender,
        profile_dir=Path(args.profile_dir),
        artifact_root=Path(args.artifact_root),
        lease_seconds=args.lease_seconds,
        headless=bool(args.headless),
        keep_open=bool(args.keep_open),
        timeout_ms=args.timeout_ms,
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
